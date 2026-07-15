import { NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";
import crypto from "crypto";

// Initialize Supabase Admin Client (Service Role bypasses RLS)
const supabaseAdmin = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL || "",
  process.env.SUPABASE_SERVICE_ROLE_KEY || "",
  {
    auth: {
      autoRefreshToken: false,
      persistSession: false,
    },
  }
);

export async function POST(request: Request) {
  try {
    const rawBody = await request.text();
    const hmacHeader = request.headers.get("x-shopify-hmac-sha256");

    // Verify Shopify HMAC Signature if secret is configured
    const shopifySecret = process.env.SHOPIFY_WEBHOOK_SECRET;
    if (shopifySecret && hmacHeader) {
      const generatedHmac = crypto
        .createHmac("sha256", shopifySecret)
        .update(rawBody, "utf8")
        .digest("base64");

      if (generatedHmac !== hmacHeader) {
        console.error("Shopify Webhook signature verification failed.");
        return NextResponse.json({ error: "Invalid HMAC signature" }, { status: 401 });
      }
    }

    const payload = JSON.parse(rawBody);
    console.log("Received Shopify webhook payload for Order:", payload.id || payload.order_number);

    // Extract customer email and line items
    const customerEmail = payload.email || payload.customer?.email;
    if (!customerEmail) {
      console.warn("No customer email found in Shopify order payload.");
      return NextResponse.json({ received: true, message: "No email attached to order" });
    }

    // Check if the order is paid
    const financialStatus = payload.financial_status; // e.g., 'paid'
    if (financialStatus !== "paid") {
      console.log(`Shopify order ${payload.id} status is '${financialStatus}', skipping tier upgrade.`);
      return NextResponse.json({ received: true, status: financialStatus });
    }

    // Check which Cronus tier was purchased: daily ($1), weekly ($5), or monthly ($25)
    const lineItems = payload.line_items || [];
    let detectedTier = "pro"; // default
    let videosLimit = 3;

    const matchedItem = lineItems.find(
      (item: { title?: string; name?: string; product_id?: number }) => {
        const title = (item.title || item.name || "").toLowerCase();
        return title.includes("cronus") || title.includes("daily") || title.includes("weekly") || title.includes("monthly") || title.includes("pro");
      }
    );

    if (!matchedItem) {
      console.log("Purchased items do not include Cronus subscription, skipping upgrade.");
      return NextResponse.json({ received: true, message: "Not a Cronus subscription purchase" });
    }

    const itemTitle = (matchedItem.title || matchedItem.name || "").toLowerCase();
    if (itemTitle.includes("daily")) {
      detectedTier = "daily";
      videosLimit = 1;
    } else if (itemTitle.includes("weekly")) {
      detectedTier = "weekly";
      videosLimit = 3;
    } else if (itemTitle.includes("monthly") || itemTitle.includes("industrial")) {
      detectedTier = "monthly";
      videosLimit = 5;
    }

    // Lookup user by email in Supabase auth.users using service_role RPC or plans table join
    const { data: usersData, error: usersError } = await supabaseAdmin.auth.admin.listUsers();
    
    if (usersError || !usersData?.users) {
      console.error("Failed to list Supabase users:", usersError?.message);
      return NextResponse.json({ error: "Database query failed" }, { status: 500 });
    }

    const matchingUser = usersData.users.find(
      (u) => (u.email || "").toLowerCase() === customerEmail.toLowerCase()
    );

    if (!matchingUser) {
      console.warn(`No matching Supabase user found with email: ${customerEmail}`);
      return NextResponse.json({ received: true, message: "User account not found for email" });
    }

    const userId = matchingUser.id;
    console.log(`Matching user found: ${userId} (${customerEmail}). Upgrading plan to ${detectedTier.toUpperCase()} (limit: ${videosLimit} videos/day).`);

    // Upsert detected plan status into plans table
    const { error: planError } = await supabaseAdmin
      .from("plans")
      .upsert(
        {
          user_id: userId,
          plan_type: detectedTier,
          subscription_status: "active",
          videos_per_day_limit: videosLimit,
          started_at: new Date().toISOString(),
        },
        { onConflict: "user_id" }
      );

    if (planError) {
      console.error("Failed to update user plan in database:", planError.message);
      throw planError;
    }

    // Also update videos_per_day limit in user_configs if row exists
    await supabaseAdmin
      .from("user_configs")
      .update({ videos_per_day: videosLimit })
      .eq("user_id", userId);

    console.log(`Successfully upgraded user ${userId} to ${detectedTier.toUpperCase()} plan via Shopify Webhook.`);
    return NextResponse.json({ success: true, user_id: userId, plan: "pro" });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Unknown error";
    console.error("Shopify Webhook processing error:", message);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
