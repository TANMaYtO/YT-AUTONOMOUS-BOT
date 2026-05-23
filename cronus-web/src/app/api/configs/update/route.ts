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

    // First fetch existing config to merge it (because upsert completely overwrites fields if not provided)
    const { data: existingConfig } = await supabase
      .from("user_configs")
      .select("*")
      .eq("user_id", user.id)
      .single();

    // Merge existing config with new body
    const updateData = {
      user_id: user.id,
      niche: body.niche !== undefined ? body.niche : existingConfig?.niche,
      topics: body.topics !== undefined ? body.topics : existingConfig?.topics,
      characters: body.characters !== undefined ? body.characters : existingConfig?.characters,
      videos_per_day: body.videos_per_day !== undefined ? body.videos_per_day : existingConfig?.videos_per_day,
      upload_times: body.upload_times !== undefined ? body.upload_times : existingConfig?.upload_times,
    };

    // Upsert into user_configs table
    const { error: configError } = await supabase
      .from("user_configs")
      .upsert(updateData, { onConflict: "user_id" });

    if (configError) {
      throw configError;
    }

    return NextResponse.json({ success: true });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Unknown error";
    console.error("Config update error:", message);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
