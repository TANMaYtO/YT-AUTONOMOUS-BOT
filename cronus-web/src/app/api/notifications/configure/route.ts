import { NextResponse, type NextRequest } from "next/server";
import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";

export async function POST(request: NextRequest) {
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

    const cookieStore = await cookies();
    const supabase = createServerClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
      {
        cookies: {
          getAll() {
            return cookieStore.getAll();
          },
          setAll(cookiesToSet) {
            try {
              cookiesToSet.forEach(({ name, value, options }) =>
                cookieStore.set(name, value, options)
              );
            } catch {}
          },
        },
      }
    );

    const { data: { user }, error: authError } = await supabase.auth.getUser();
    
    if (authError || !user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    // Update user_configs with notification settings
    const { error: updateError } = await supabase
      .from("user_configs")
      .upsert({
        user_id: user.id,
        telegram_bot_token,
        telegram_chat_id,
        daily_summary: !!daily_summary,
        failure_alerts: !!failure_alerts,
        updated_at: new Date().toISOString(),
      }, {
        onConflict: 'user_id',
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
