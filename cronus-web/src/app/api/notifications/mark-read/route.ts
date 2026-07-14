import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

export async function PATCH() {
  try {
    const supabase = await createClient();
    
    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser();

    if (authError || !user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    // Mark all unread notifications for this user as read
    const { error: updateError } = await supabase
      .from("app_notifications")
      .update({ read: true })
      .eq("user_id", user.id)
      .eq("read", false);

    if (updateError) {
      throw updateError;
    }

    return NextResponse.json({ success: true });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Unknown error";
    console.error("Mark notifications read error:", message);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
