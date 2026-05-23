import { NextRequest, NextResponse } from "next/server";
import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";
import crypto from "crypto";

// Helper to encrypt tokens using AES-GCM
// Expects TOKEN_ENCRYPTION_KEY to be a 64-character hex string (32 bytes)
function encryptToken(text: string | null | undefined): string | null {
  if (!text) return null;
  const keyString = process.env.TOKEN_ENCRYPTION_KEY;
  if (!keyString) throw new Error("TOKEN_ENCRYPTION_KEY is not set");
  
  const key = Buffer.from(keyString, "hex");
  const iv = crypto.randomBytes(12); // 12 bytes is standard for GCM
  const cipher = crypto.createCipheriv("aes-256-gcm", key, iv);
  
  let encrypted = cipher.update(text, "utf8", "hex");
  encrypted += cipher.final("hex");
  const authTag = cipher.getAuthTag().toString("hex");
  
  // Format: iv:authTag:encrypted
  return `${iv.toString("hex")}:${authTag}:${encrypted}`;
}

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const code = searchParams.get("code");
  const state = searchParams.get("state");
  const error = searchParams.get("error");
  
  const cookieStore = await cookies();
  const savedState = cookieStore.get("cronus_oauth_state")?.value;

  // Base URL for error redirects
  const errorRedirectUrl = request.nextUrl.clone();
  errorRedirectUrl.pathname = "/onboard/youtube";
  errorRedirectUrl.searchParams.set("error", "connection_failed");

  // Handle user denial or missing params
  if (error || !code || !state || state !== savedState) {
    console.error("OAuth Validation Failed:", { error, codeExists: !!code, stateMatches: state === savedState });
    return NextResponse.redirect(errorRedirectUrl);
  }

  try {
    // 1. Initialize Supabase and check Auth
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
      throw new Error("Unauthorized: No active session");
    }

    // 2. Exchange Code for Tokens
    const tokenResponse = await fetch("https://oauth2.googleapis.com/token", {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: new URLSearchParams({
        client_id: process.env.YOUTUBE_CLIENT_ID!,
        client_secret: process.env.YOUTUBE_CLIENT_SECRET!,
        code: code,
        redirect_uri: process.env.YOUTUBE_REDIRECT_URI!,
        grant_type: "authorization_code",
      }),
    });

    if (!tokenResponse.ok) {
      const errText = await tokenResponse.text();
      throw new Error(`Token exchange failed: ${errText}`);
    }

    const tokenData = await tokenResponse.json();
    const { access_token, refresh_token, expires_in } = tokenData;

    // 3. Fetch YouTube Channel Info
    const channelResponse = await fetch(
      "https://www.googleapis.com/youtube/v3/channels?part=snippet,statistics&mine=true",
      {
        headers: {
          Authorization: `Bearer ${access_token}`,
        },
      }
    );

    if (!channelResponse.ok) {
      const errText = await channelResponse.text();
      throw new Error(`Channel fetch failed: ${errText}`);
    }

    const channelData = await channelResponse.json();
    const channel = channelData.items?.[0];

    if (!channel) {
      throw new Error("No YouTube channel found for this account");
    }

    const channelId = channel.id;
    const channelName = channel.snippet.title;
    const subscriberCount = parseInt(channel.statistics.subscriberCount, 10) || 0;

    // 4. Encrypt tokens
    const encryptedAccessToken = encryptToken(access_token);
    const encryptedRefreshToken = encryptToken(refresh_token); // might be undefined if not prompted

    const tokenExpiry = new Date(Date.now() + expires_in * 1000).toISOString();

    // 5. Upsert to youtube_connections table
    const { error: dbError } = await supabase
      .from("youtube_connections")
      .upsert({
        user_id: user.id,
        channel_id: channelId,
        channel_name: channelName,
        subscriber_count: subscriberCount,
        access_token: encryptedAccessToken,
        // Only update refresh token if a new one was provided
        ...(encryptedRefreshToken ? { refresh_token: encryptedRefreshToken } : {}),
        token_expiry: tokenExpiry,
        connected_at: new Date().toISOString(),
      }, {
        onConflict: 'user_id',
      });

    if (dbError) {
      throw new Error(`Database upsert failed: ${dbError.message}`);
    }

    // Clean up the state cookie
    cookieStore.delete("cronus_oauth_state");

    // 6. Redirect to Niche selection step
    const successUrl = request.nextUrl.clone();
    successUrl.pathname = "/onboard/niche";
    successUrl.search = ""; // clear any query params
    return NextResponse.redirect(successUrl);

  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Unknown error";
    console.error("YouTube OAuth Error:", message);
    return NextResponse.redirect(errorRedirectUrl);
  }
}
