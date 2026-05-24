import Link from "next/link";
import { LayoutDashboard, Settings, Video, Banknote } from "lucide-react";
import { SignOutButton } from "./sign-out-button";

export function Sidebar() {
  return (
    <aside className="w-64 border-r-2 border-cronus-gray/30 bg-cronus-surface flex flex-col min-h-screen">
      <div className="h-16 flex items-center px-6 border-b-2 border-cronus-gray/30">
        <Video className="w-6 h-6 text-cronus-red mr-3" />
        <span className="font-sans font-bold text-xl tracking-tighter uppercase">
          Cronus<span className="text-cronus-red">_</span>
        </span>
      </div>

      <nav className="flex-1 p-4 space-y-2 font-mono">
        <Link
          href="/dashboard"
          className="flex items-center px-4 py-3 text-sm hover:bg-cronus-red/10 border-2 border-transparent hover:border-cronus-red transition-colors uppercase"
        >
          <LayoutDashboard className="w-4 h-4 mr-3" />
          Dashboard
        </Link>
        <Link
          href="/dashboard/settings"
          className="flex items-center px-4 py-3 text-sm hover:bg-cronus-red/10 border-2 border-transparent hover:border-cronus-red transition-colors uppercase"
        >
          <Settings className="w-4 h-4 mr-3" />
          Settings
        </Link>
        <Link
          href="/dashboard/pricing"
          className="flex items-center px-4 py-3 text-sm hover:bg-cronus-red/10 border-2 border-transparent hover:border-cronus-red transition-colors uppercase"
        >
          <Banknote className="w-4 h-4 mr-3" />
          Pricing
        </Link>
      </nav>

      <div className="p-4 border-t-2 border-cronus-gray/30">
        <div className="mb-4">
          <p className="font-mono text-xs text-cronus-gray mb-1 uppercase">Agent Status</p>
          <div className="flex items-center text-sm font-mono border-2 border-cronus-gray/30 p-2 bg-cronus-bg">
            <span className="w-2 h-2 rounded-none bg-green-500 mr-2 animate-pulse"></span>
            RUNNING
          </div>
        </div>

        <SignOutButton />
      </div>
    </aside>
  );
}
