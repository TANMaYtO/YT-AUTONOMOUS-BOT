import { NextResponse } from "next/server";
import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";

export async function GET() {
  try {
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

    const { data: config, error: configError } = await supabase
      .from("user_configs")
      .select("is_active, last_run_at")
      .eq("user_id", user.id)
      .single();

    if (configError && configError.code !== "PGRST116") {
      // PGRST116 means no rows found, which is fine, they just don't have a config yet
      throw new Error(`Database error: ${configError.message}`);
    }

    const isActive = config?.is_active ?? false;
    const lastRunAt = config?.last_run_at ?? null;

    return NextResponse.json({
      status: isActive ? "running" : "idle",
      next_run: "01:00 IST", // Hardcoded based on project specs
      last_run: lastRunAt,
    });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Unknown error";
    console.error("Agent Status Error:", message);
    return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
  }
}
