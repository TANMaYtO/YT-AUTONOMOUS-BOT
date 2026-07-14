import { NextResponse } from "next/server";
import { headers } from "next/headers";
import Stripe from "stripe";
import { createClient } from "@supabase/supabase-js";

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY || "sk_test_placeholder", {
  apiVersion: "2024-06-20" as any,
});

// Use service role key to bypass RLS inside webhooks
const supabaseAdmin = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
);

export async function POST(request: Request) {
  const body = await request.text();
  const headersList = await headers();
  const signature = headersList.get("stripe-signature");

  let event: Stripe.Event;

  try {
    if (!signature || !process.env.STRIPE_WEBHOOK_SECRET) {
      return NextResponse.json({ error: "Missing signature or webhook secret" }, { status: 400 });
    }
    event = stripe.webhooks.constructEvent(body, signature, process.env.STRIPE_WEBHOOK_SECRET);
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Unknown error";
    console.error("Stripe Webhook Signature Verification Failed:", message);
    return NextResponse.json({ error: "Webhook Error: " + message }, { status: 400 });
  }

  try {
    switch (event.type) {
      case "checkout.session.completed": {
        const session = event.data.object as Stripe.Checkout.Session;
        const userId = session.metadata?.user_id;

        if (userId) {
          await supabaseAdmin
            .from("plans")
            .upsert({
              user_id: userId,
              plan_type: "pro",
              videos_per_day_limit: 3,
              stripe_customer_id: session.customer as string,
              stripe_subscription_id: session.subscription as string,
              subscription_status: "active",
              started_at: new Date().toISOString(),
            }, { onConflict: "user_id" });

          // Also push an in-app success notification
          await supabaseAdmin.from("app_notifications").insert({
            user_id: userId,
            type: "success",
            title: "Pro Subscription Activated! 🚀",
            message: "Welcome to Cronus Pro! Your daily video limit is now increased to 3 videos per day.",
            metadata: { stripe_session_id: session.id },
          });
        }
        break;
      }

      case "invoice.payment_succeeded": {
        const invoice = event.data.object as Stripe.Invoice;
        const customerId = invoice.customer as string;

        // Find user by customer ID
        const { data: planData } = await supabaseAdmin
          .from("plans")
          .select("user_id")
          .eq("stripe_customer_id", customerId)
          .single();

        if (planData?.user_id) {
          await supabaseAdmin
            .from("plans")
            .update({
              subscription_status: "active",
            })
            .eq("user_id", planData.user_id);
        }
        break;
      }

      case "customer.subscription.deleted":
      case "customer.subscription.updated": {
        const sub = event.data.object as Stripe.Subscription;
        const customerId = sub.customer as string;

        const { data: planData } = await supabaseAdmin
          .from("plans")
          .select("user_id")
          .eq("stripe_customer_id", customerId)
          .single();

        if (planData?.user_id) {
          const isActive = sub.status === "active" || sub.status === "trialing";
          await supabaseAdmin
            .from("plans")
            .update({
              plan_type: isActive ? "pro" : "free",
              videos_per_day_limit: isActive ? 3 : 1,
              subscription_status: sub.status,
            })
            .eq("user_id", planData.user_id);
        }
        break;
      }
    }

    return NextResponse.json({ received: true });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Unknown error";
    console.error("Webhook processing error:", message);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
