"use client";

import Link from "next/link";
import { User } from "lucide-react";
import { useState, useEffect } from "react";
import { createClient } from "@/lib/supabase/client";
import { NotificationBell } from "@/components/notification-bell";

export function Navbar() {
  const [email, setEmail] = useState("");
  const [userId, setUserId] = useState<string>("");

  useEffect(() => {
    const fetchUser = async () => {
      const supabase = createClient();
      const { data: { user } } = await supabase.auth.getUser();
      if (user) {
        setUserId(user.id);
        if (user.email) {
          setEmail(user.email.split("@")[0]);
        }
      }
    };
    
    fetchUser();
  }, []);

  return (
    <header className="h-16 border-b-2 border-cronus-gray/30 bg-cronus-surface flex items-center justify-between px-8">
      <div className="flex items-center space-x-4">
        <h2 className="font-sans font-bold text-lg uppercase tracking-widest text-cronus-gray">
          Terminal Session
        </h2>
      </div>

      <div className="flex items-center space-x-4">
        {userId && <NotificationBell userId={userId} />}
        
        <div className="flex items-center border-2 border-cronus-gray/30 p-1 pr-4">
          <div className="w-8 h-8 bg-cronus-red flex items-center justify-center mr-3">
            <User className="w-4 h-4 text-cronus-white" />
          </div>
          <span className="font-mono text-sm uppercase">{email || "..."}</span>
        </div>
      </div>
    </header>
  );
}
