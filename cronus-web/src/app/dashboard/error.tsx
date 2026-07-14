"use client";

import { useEffect } from "react";
import { AlertTriangle, RefreshCcw } from "lucide-react";

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Dashboard error:", error);
  }, [error]);

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] p-8 text-center bg-cronus-bg border-2 border-cronus-red m-8 shadow-[8px_8px_0px_0px_rgba(255,34,0,0.3)]">
      <div className="w-16 h-16 bg-cronus-red flex items-center justify-center mb-6">
        <AlertTriangle className="w-8 h-8 text-cronus-white" />
      </div>
      <h2 className="font-sans font-bold text-2xl uppercase text-cronus-white mb-2 tracking-wide">
        SYSTEM_EXCEPTION_DETECTED
      </h2>
      <p className="font-mono text-sm text-cronus-gray max-w-md mb-8">
        {error.message || "An unexpected error occurred while rendering this terminal session view."}
      </p>
      <button
        onClick={() => reset()}
        className="px-6 py-3 bg-cronus-red text-cronus-white font-mono text-xs font-bold uppercase tracking-widest hover:bg-cronus-white hover:text-cronus-bg transition-colors flex items-center"
      >
        <RefreshCcw className="w-4 h-4 mr-2" /> [RETRY_TRANSACTION]
      </button>
    </div>
  );
}
