import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import crypto from "crypto";

export async function GET() {
  const state = crypto.randomUUID();
  const cookieStore = await cookies();

  cookieStore.set("cronus_oauth_state", state, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    maxAge: 600, // 10 minutes
  });

  const authUrl = new URL("https://accounts.google.com/o/oauth2/v2/auth");
  authUrl.searchParams.set("client_id", process.env.YOUTUBE_CLIENT_ID!);
  authUrl.searchParams.set("redirect_uri", process.env.YOUTUBE_REDIRECT_URI!);
  authUrl.searchParams.set("response_type", "code");
  // We need youtube.upload for uploading, and youtube.readonly for channel stats
  authUrl.searchParams.set(
    "scope",
    "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly"
  );
  authUrl.searchParams.set("access_type", "offline");
  authUrl.searchParams.set("prompt", "consent");
  authUrl.searchParams.set("state", state);

  return NextResponse.redirect(authUrl.toString());
}
