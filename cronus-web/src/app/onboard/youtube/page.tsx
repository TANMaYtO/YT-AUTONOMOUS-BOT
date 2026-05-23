"use client";

import { useRouter } from "next/navigation";
import { ProgressBar } from "@/components/onboard/progress-bar";
import { Check, X, ArrowRight, Play } from "lucide-react";

export default function YoutubeStep() {
  const router = useRouter();

  return (
    <div className="min-h-screen bg-cronus-bg flex flex-col items-center">
      <ProgressBar currentStep={1} />

      <main className="flex-1 w-full max-w-4xl mx-auto flex flex-col items-center justify-center p-6">
        <h1 className="font-sans font-bold text-5xl uppercase mb-12 text-cronus-white text-center">
          CONNECT YOUTUBE
          <span className="text-cronus-red">_</span>
        </h1>

        <div className="w-full flex flex-col md:flex-row gap-8 mb-12">
          {/* Left Column: OAuth */}
          <div className="flex-1 border-2 border-cronus-gray/30 p-8 bg-cronus-surface shadow-[8px_8px_0px_0px_rgba(136,136,136,0.3)]">
            <h2 className="font-mono text-xl uppercase mb-6 text-cronus-white">Authorization</h2>
            <p className="font-mono text-sm text-cronus-gray mb-8">
              Cronus requires a direct connection to your YouTube channel to upload the generated shorts automatically.
            </p>

            <a
              href="/api/auth/youtube/initiate"
              className="w-full flex items-center justify-center px-6 py-4 border-2 font-sans font-bold text-lg uppercase transition-all border-cronus-white bg-cronus-white text-cronus-bg hover:bg-cronus-bg hover:text-cronus-white shadow-[4px_4px_0px_0px_rgba(255,255,255,1)] hover:shadow-none translate-x-0 hover:translate-x-1 hover:translate-y-1"
            >
              <Play className="w-5 h-5 mr-3" />
              CONNECT WITH GOOGLE
            </a>
          </div>

          {/* Right Column: Permissions Info */}
          <div className="flex-1 border-2 border-cronus-gray/30 p-8 bg-cronus-surface">
            <h2 className="font-mono text-xl uppercase mb-6 text-cronus-white">WHAT WE ACCESS</h2>
            
            <ul className="space-y-4 font-mono text-sm">
              <li className="flex items-start text-cronus-white">
                <Check className="w-5 h-5 text-green-500 mr-3 shrink-0" />
                <span>Upload videos to your channel</span>
              </li>
              <li className="flex items-start text-cronus-white">
                <Check className="w-5 h-5 text-green-500 mr-3 shrink-0" />
                <span>Read your YouTube analytics</span>
              </li>
              <li className="flex items-start text-cronus-gray pt-4 border-t-2 border-cronus-gray/30">
                <X className="w-5 h-5 text-cronus-red mr-3 shrink-0" />
                <span>Delete your videos</span>
              </li>
              <li className="flex items-start text-cronus-gray">
                <X className="w-5 h-5 text-cronus-red mr-3 shrink-0" />
                <span>Change your password or settings</span>
              </li>
            </ul>
          </div>
        </div>

        <button
          onClick={() => router.push("/onboard/niche")}
          className="w-full max-w-md flex items-center justify-center font-sans font-bold text-xl uppercase px-8 py-4 border-2 transition-all bg-cronus-red text-cronus-white border-cronus-red hover:bg-cronus-bg hover:text-cronus-red shadow-[8px_8px_0px_0px_rgba(255,34,0,0.3)] hover:shadow-none hover:translate-x-2 hover:translate-y-2 cursor-pointer"
        >
          CONTINUE <ArrowRight className="ml-3 w-6 h-6" />
        </button>
      </main>
    </div>
  );
}
