"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ProgressBar } from "@/components/onboard/progress-bar";
import { ArrowRight, Clock, Info } from "lucide-react";

const HOURS = Array.from({ length: 18 }, (_, i) => {
  const h = i + 6;
  return `${h.toString().padStart(2, "0")}:00`;
});

export default function ScheduleStep() {
  const router = useRouter();
  const [videosPerDay, setVideosPerDay] = useState(3);
  const [uploadTimes, setUploadTimes] = useState(["09:00", "15:00", "20:00"]);

  const handleVideosChange = (num: number) => {
    setVideosPerDay(num);
    // Keep existing times or slice/default based on the new number
    const defaultTimes = ["09:00", "15:00", "20:00"];
    setUploadTimes(defaultTimes.slice(0, num));
  };

  const handleTimeChange = (index: number, newTime: string) => {
    const newTimes = [...uploadTimes];
    newTimes[index] = newTime;
    setUploadTimes(newTimes);
  };

  const handleLaunch = () => {
    // In Phase 2: save config to Supabase first
    router.push("/dashboard");
  };

  return (
    <div className="min-h-screen bg-cronus-bg flex flex-col items-center">
      <ProgressBar currentStep={3} />

      <main className="flex-1 w-full max-w-3xl mx-auto flex flex-col items-center justify-center p-6 py-12">
        <h1 className="font-sans font-bold text-5xl uppercase mb-12 text-cronus-white text-center">
          CONFIGURE ENGINE
          <span className="text-cronus-red">_</span>
        </h1>

        <div className="w-full border-2 border-cronus-gray/30 p-8 bg-cronus-surface shadow-[8px_8px_0px_0px_rgba(136,136,136,0.3)] mb-12">
          {/* Videos Per Day */}
          <section className="mb-10">
            <h2 className="font-mono text-xl uppercase mb-6 text-cronus-white">Output Volume</h2>
            <div className="flex gap-4">
              {[1, 2, 3].map((num) => (
                <button
                  key={num}
                  onClick={() => handleVideosChange(num)}
                  className={`w-16 h-16 flex items-center justify-center font-sans font-bold text-2xl border-2 transition-all ${
                    videosPerDay === num
                      ? "bg-cronus-red border-cronus-red text-cronus-bg shadow-[4px_4px_0px_0px_rgba(255,34,0,0.3)]"
                      : "bg-cronus-bg border-cronus-gray text-cronus-white hover:border-cronus-white"
                  }`}
                >
                  {num}
                </button>
              ))}
              <span className="ml-4 font-mono text-sm text-cronus-gray self-end mb-2 uppercase">Videos / Day</span>
            </div>
          </section>

          {/* Upload Times */}
          <section className="mb-10">
            <h2 className="font-mono text-xl uppercase mb-6 text-cronus-white">Upload Schedule</h2>
            <div className="flex flex-col gap-4">
              {Array.from({ length: videosPerDay }).map((_, index) => (
                <div key={index} className="flex items-center">
                  <div className="w-8 h-8 bg-cronus-gray/20 flex items-center justify-center mr-4 font-mono text-sm text-cronus-white border-2 border-cronus-gray/30">
                    {index + 1}
                  </div>
                  <div className="relative flex-1 max-w-[200px]">
                    <Clock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-cronus-gray" />
                    <select
                      value={uploadTimes[index]}
                      onChange={(e) => handleTimeChange(index, e.target.value)}
                      className="w-full bg-cronus-bg border-2 border-cronus-gray/30 text-cronus-white pl-10 pr-4 py-3 font-mono text-sm uppercase appearance-none focus:outline-none focus:border-cronus-red transition-colors cursor-pointer"
                    >
                      {HOURS.map((hour) => (
                        <option key={hour} value={hour}>
                          {hour}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Generation Info */}
          <div className="flex items-start p-4 border-2 border-cronus-gray bg-cronus-bg">
            <Info className="w-5 h-5 text-cronus-gray mr-3 shrink-0 mt-0.5" />
            <div>
              <p className="font-mono text-sm uppercase text-cronus-white font-bold">Fixed Generation Cycle</p>
              <p className="font-mono text-xs text-cronus-gray mt-1">Cronus generates all videos at 01:00 IST daily. This allows ample time for rendering and QA before scheduled upload times.</p>
            </div>
          </div>
        </div>

        <button
          onClick={handleLaunch}
          className="w-full flex items-center justify-center font-sans font-bold text-2xl uppercase py-6 bg-cronus-red text-cronus-white border-2 border-cronus-red hover:bg-cronus-bg hover:text-cronus-red transition-all shadow-[8px_8px_0px_0px_rgba(255,34,0,0.3)] hover:shadow-none hover:translate-x-2 hover:translate-y-2 mb-6"
        >
          LAUNCH CRONUS <ArrowRight className="ml-3 w-8 h-8" />
        </button>
        <p className="font-mono text-xs text-cronus-gray uppercase tracking-widest text-center">
          YOU CAN CHANGE ALL SETTINGS ANYTIME FROM THE DASHBOARD
        </p>
      </main>
    </div>
  );
}
