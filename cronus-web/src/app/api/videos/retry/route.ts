import { NextResponse, type NextRequest } from "next/server";
import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { video_id } = body;

    if (!video_id) {
      return NextResponse.json({ error: "video_id is required" }, { status: 400 });
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

    // Find the video and verify ownership
    const { data: video, error: fetchError } = await supabase
      .from("videos")
      .select("id, status")
      .eq("id", video_id)
      .eq("user_id", user.id)
      .single();

    if (fetchError || !video) {
      return NextResponse.json({ error: "Video not found or access denied" }, { status: 403 });
    }

    if (video.status !== "failed") {
      return NextResponse.json({ error: "Only failed videos can be retried" }, { status: 400 });
    }

    // Reset status and clear error
    const { error: updateError } = await supabase
      .from("videos")
      .update({
        status: "pending",
        error_message: null,
        updated_at: new Date().toISOString(),
      })
      .eq("id", video_id)
      .eq("user_id", user.id);

    if (updateError) {
      throw new Error(`Database update failed: ${updateError.message}`);
    }

    return NextResponse.json({ success: true });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Unknown error";
    console.error("Video Retry Error:", message);
    return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
  }
}
