import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import Stripe from "stripe";

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY || "sk_test_placeholder", {
  apiVersion: "2024-06-20",
});

export async function POST(request: Request) {
  try {
    const supabase = await createClient();
    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser();

    if (authError || !user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const body = await request.json();
    const { priceId, returnUrl, planType } = body; // planType: 'daily', 'weekly', 'monthly', 'pro'

    // Check if Shopify Checkout URL is configured for the selected tier (or fallback to general Shopify URL)
    const tierKey = (planType || "").toUpperCase();
    const shopifyCheckoutUrl = 
      process.env[`SHOPIFY_CHECKOUT_URL_${tierKey}`] ||
      process.env.SHOPIFY_CHECKOUT_URL || 
      process.env.NEXT_PUBLIC_SHOPIFY_CHECKOUT_URL;

    if (shopifyCheckoutUrl && (!process.env.STRIPE_SECRET_KEY || process.env.STRIPE_SECRET_KEY.includes("placeholder") || process.env.USE_SHOPIFY_CHECKOUT === "true")) {
      return NextResponse.json({ url: shopifyCheckoutUrl });
    }

    // Resolve tier-specific Stripe Price ID
    const resolvedPriceId = priceId || process.env[`STRIPE_PRICE_ID_${tierKey}`] || process.env.STRIPE_PRO_PRICE_ID || "price_pro_placeholder";

    // Check existing customer ID from plans table
    const { data: planData } = await supabase
      .from("plans")
      .select("stripe_customer_id")
      .eq("user_id", user.id)
      .single();

    let customerId = planData?.stripe_customer_id;

    if (!customerId) {
      const customer = await stripe.customers.create({
        email: user.email,
        metadata: {
          user_id: user.id,
        },
      });
      customerId = customer.id;

      // Save customer ID
      await supabase
        .from("plans")
        .upsert({
          user_id: user.id,
          stripe_customer_id: customerId,
        }, { onConflict: "user_id" });
    }

    const session = await stripe.checkout.sessions.create({
      customer: customerId,
      mode: "subscription",
      payment_method_types: ["card"],
      line_items: [
        {
          price: resolvedPriceId,
          quantity: 1,
        },
      ],
      success_url: `${returnUrl || process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000"}/dashboard?checkout=success`,
      cancel_url: `${returnUrl || process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000"}/onboard/plan?checkout=cancelled`,
      metadata: {
        user_id: user.id,
      },
    });

    return NextResponse.json({ url: session.url });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Unknown error";
    console.error("Stripe Checkout Error:", message);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
