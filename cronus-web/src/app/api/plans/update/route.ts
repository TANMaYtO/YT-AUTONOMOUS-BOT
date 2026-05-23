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

    return NextResponse.json({ success: true, plan_type: planType });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Unknown error";
    console.error("Plan update error:", message);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
