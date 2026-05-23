import Link from "next/link";
import { User, Bell } from "lucide-react";

export function Navbar() {
  return (
    <header className="h-16 border-b-2 border-cronus-gray/30 bg-cronus-surface flex items-center justify-between px-8">
      <div className="flex items-center space-x-4">
        <h2 className="font-sans font-bold text-lg uppercase tracking-widest text-cronus-gray">
          Terminal Session
        </h2>
      </div>

      <div className="flex items-center space-x-4">
        <button className="p-2 border-2 border-cronus-gray/30 hover:border-cronus-red transition-colors relative">
          <Bell className="w-5 h-5 text-cronus-white" />
          <span className="absolute top-0 right-0 w-2 h-2 bg-cronus-red translate-x-1 -translate-y-1 border border-cronus-surface" />
        </button>
        <div className="flex items-center border-2 border-cronus-gray/30 p-1 pr-4">
          <div className="w-8 h-8 bg-cronus-red flex items-center justify-center mr-3">
            <User className="w-4 h-4 text-cronus-white" />
          </div>
          {/* TODO: Replace hardcoded Admin with user email from Supabase session */}
          <span className="font-mono text-sm uppercase">Admin</span>
        </div>
      </div>
    </header>
  );
}
