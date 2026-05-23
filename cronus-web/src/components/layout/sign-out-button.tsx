"use client";

import { LogOut } from "lucide-react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";

export function SignOutButton() {
  const router = useRouter();

  const handleSignOut = async () => {
    const supabase = createClient();
    await supabase.auth.signOut();
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
