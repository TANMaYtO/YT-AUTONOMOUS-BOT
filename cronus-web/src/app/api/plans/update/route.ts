import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

export async function POST(request: Request) {
  try {
    const supabase = await createClient();
    
    // Check auth
    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser();

    if (authError || !user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const body = await request.json();
    const { planType } = body; // 'free' or 'pro'

    if (!["free", "pro"].includes(planType)) {
      return NextResponse.json({ error: "Invalid plan type" }, { status: 400 });
    }

    // SECURITY / MONETIZATION GUARD:
    // Pro plan upgrades MUST go through Stripe Checkout via /api/payments/create-checkout + webhook.
    // We disallow self-upgrades to "pro" via this free update endpoint unless user is already pro.
    if (planType === "pro") {
      const { data: existingPlan } = await supabase
        .from("plans")
        .select("plan_type, subscription_status")
        .eq("user_id", user.id)
        .single();

      if (existingPlan?.plan_type !== "pro" || existingPlan?.subscription_status !== "active") {
        return NextResponse.json(
          { error: "Pro plan requires active Stripe checkout subscription. Please use checkout." },
          { status: 403 }
        );
      }
    }

    const videosPerDay = planType === "pro" ? 3 : 1;

    // Upsert into plans table
    const { error: planError } = await supabase
      .from("plans")
      .upsert({
        user_id: user.id,
        plan_type: planType,
        videos_per_day_limit: videosPerDay,
        started_at: new Date().toISOString(),
      }, { onConflict: "user_id" });

    if (planError) {
      throw planError;
    }

    // Create a default user_configs row for new users so the Python agent never crashes
    const { error: configError } = await supabase
      .from("user_configs")
      .upsert(
        {
          user_id: user.id,
          topics: ["What is AI?", "Python vs JavaScript", "How does the internet work?"],
          characters: [],
          videos_per_day: videosPerDay,
          upload_times: ["09:00"],
          is_active: false,
          niche: "tech",
        },
        { onConflict: "user_id", ignoreDuplicates: true }
      );

    if (configError) {
      // Non-fatal: log but don't fail the plan update
      console.error("Warning: Could not create default user_configs row:", configError.message);
    }

    return NextResponse.json({ success: true, plan_type: planType });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Unknown error";
    console.error("Plan update error:", message);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
