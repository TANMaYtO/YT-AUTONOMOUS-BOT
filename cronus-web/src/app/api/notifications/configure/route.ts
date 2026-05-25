import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { telegram_bot_token, telegram_chat_id, daily_summary, failure_alerts } = body;

    if (!telegram_bot_token || !telegram_chat_id) {
      return NextResponse.json({ error: "Token and Chat ID are required" }, { status: 400 });
    }

    // Validate token format (starts with digits followed by a colon)
    const tokenRegex = /^\d+:[A-Za-z0-9_-]+$/;
    if (!tokenRegex.test(telegram_bot_token)) {
      return NextResponse.json({ error: "Invalid Telegram bot token format" }, { status: 400 });
    }

    // Test the bot token by calling Telegram API
    const tgResponse = await fetch(`https://api.telegram.org/bot${telegram_bot_token}/getMe`);
    if (!tgResponse.ok) {
      return NextResponse.json({ error: "Failed to verify bot token with Telegram" }, { status: 400 });
    }

    const tgData = await tgResponse.json();
    if (!tgData.ok) {
      return NextResponse.json({ error: "Telegram API rejected the token" }, { status: 400 });
    }

    const supabase = await createClient();

    const { data: { user }, error: authError } = await supabase.auth.getUser();

    if (authError || !user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    // Fetch existing config to preserve non-notification fields
    const { data: existingConfig } = await supabase
      .from("user_configs")
      .select("*")
      .eq("user_id", user.id)
      .single();

    // Merge notification fields into existing config to prevent data loss
    const updateData = {
      ...existingConfig,
      user_id: user.id,
      telegram_bot_token,
      telegram_chat_id,
      daily_summary: !!daily_summary,
      failure_alerts: !!failure_alerts,
      updated_at: new Date().toISOString(),
    };

    const { error: updateError } = await supabase
      .from("user_configs")
      .upsert(updateData, {
        onConflict: "user_id",
      });

    if (updateError) {
      throw new Error(`Database update failed: ${updateError.message}`);
    }

    return NextResponse.json({ success: true });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Unknown error";
    console.error("Notifications Config Error:", message);
    return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
  }
}
