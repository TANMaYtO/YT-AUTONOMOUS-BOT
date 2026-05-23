"use client";

import { LogOut } from "lucide-react";
import { useRouter } from "next/navigation";
import { createBrowserClient } from "@supabase/ssr";

export function SignOutButton() {
  const router = useRouter();

  const handleSignOut = async () => {
    // We will initialize supabase properly in Phase 2
    // const supabase = createBrowserClient(
    //   process.env.NEXT_PUBLIC_SUPABASE_URL!,
    //   process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
    // );
    // const { error } = await supabase.auth.signOut();
    
    // For now, simulate sign out
    router.push("/auth");
  };

  return (
    <button
      onClick={handleSignOut}
      className="w-full flex items-center justify-center px-4 py-3 text-sm font-mono border-2 border-cronus-gray/30 hover:border-cronus-red hover:text-cronus-red transition-colors uppercase"
    >
      <LogOut className="w-4 h-4 mr-2" />
      Sign Out
    </button>
  );
}
