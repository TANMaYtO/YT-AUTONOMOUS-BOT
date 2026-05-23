"use client";

import { Check } from "lucide-react";
import { useState } from "react";

interface PricingPlansProps {
  onPlanSelect: (planType: string) => Promise<void>;
  loadingPlan?: string | null;
}

export function PricingPlans({ onPlanSelect, loadingPlan }: PricingPlansProps) {
  return (
    <div className="w-full max-w-6xl mx-auto flex flex-col h-full">
      <div className="mb-12">
        <div className="font-mono text-cronus-red text-sm uppercase tracking-widest font-bold mb-2">
          SELECT_SYSTEM_CAPACITY
        </div>
        <h1 className="font-sans font-bold text-5xl uppercase text-cronus-white">
          CRONUS / PLANS
        </h1>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 flex-1 border-t-2 border-cronus-red pt-12">
        {/* Basic Core */}
        <div className="flex flex-col border-r-2 border-transparent md:border-cronus-gray/30 pr-8">
          <div className="mb-8">
            <h2 className="font-sans font-bold text-2xl text-cronus-white uppercase mb-4">
              BASIC_CORE
            </h2>
            <div className="flex items-baseline text-cronus-white font-sans font-bold">
              <span className="text-6xl tracking-tighter">₹0</span>
              <span className="text-sm font-mono text-cronus-gray ml-2">/mo</span>
            </div>
          </div>
          
          <div className="border-t-2 border-cronus-white mb-8"></div>

          <ul className="space-y-4 mb-12 flex-1 font-sans text-sm text-cronus-white">
            <li className="flex items-center">
              <Check className="w-5 h-5 text-cronus-red mr-3" strokeWidth={3} />
              1 Video/Day
            </li>
            <li className="flex items-center">
              <Check className="w-5 h-5 text-cronus-red mr-3" strokeWidth={3} />
              Standard Characters
            </li>
            <li className="flex items-center">
              <Check className="w-5 h-5 text-cronus-red mr-3" strokeWidth={3} />
              YouTube Watermark
            </li>
          </ul>

          <button
            onClick={() => onPlanSelect("free")}
            disabled={!!loadingPlan}
            className="w-full py-4 font-mono text-sm text-cronus-white border-2 border-transparent hover:border-cronus-white transition-colors uppercase disabled:opacity-50"
          >
            {loadingPlan === "free" ? "[PROCESSING...]" : "[SELECT_CORE]"}
          </button>
        </div>

        {/* Industrial Pro */}
        <div className="flex flex-col relative border-2 border-cronus-red bg-cronus-bg p-8 -mt-8 shadow-[8px_8px_0px_0px_rgba(255,34,0,0.2)]">
          <div className="absolute top-0 left-0 bg-cronus-red text-cronus-white font-mono text-xs font-bold uppercase px-3 py-1 tracking-widest -translate-y-full">
            MOST_POPULAR
          </div>
          <div className="mb-8 mt-4">
            <h2 className="font-sans font-bold text-2xl text-cronus-white uppercase mb-4">
              INDUSTRIAL_PRO
            </h2>
            <div className="flex items-baseline text-cronus-red font-sans font-bold">
              <span className="text-6xl tracking-tighter">₹299</span>
              <span className="text-sm font-mono text-cronus-gray ml-2">/mo</span>
            </div>
          </div>
          
          <div className="border-t-2 border-cronus-red mb-8"></div>

          <ul className="space-y-4 mb-12 flex-1 font-sans text-sm text-cronus-white">
            <li className="flex items-center">
              <Check className="w-5 h-5 text-cronus-red mr-3" strokeWidth={3} />
              3 Videos/Day
            </li>
            <li className="flex items-center">
              <Check className="w-5 h-5 text-cronus-red mr-3" strokeWidth={3} />
              Premium Characters
            </li>
            <li className="flex items-center">
              <Check className="w-5 h-5 text-cronus-red mr-3" strokeWidth={3} />
              No Watermark
            </li>
            <li className="flex items-center">
              <Check className="w-5 h-5 text-cronus-red mr-3" strokeWidth={3} />
              Priority Processing
            </li>
          </ul>

          <button
            onClick={() => onPlanSelect("pro")}
            disabled={!!loadingPlan}
            className="w-full py-4 bg-cronus-red text-cronus-white font-mono text-sm font-bold uppercase hover:bg-cronus-white hover:text-cronus-bg transition-colors disabled:opacity-50"
          >
            {loadingPlan === "pro" ? "[PROCESSING...]" : "[SELECT_INDUSTRIAL]"}
          </button>
        </div>
      </div>

      <div className="mt-16 pt-8 border-t-2 border-cronus-red text-center font-mono text-[10px] text-cronus-gray tracking-widest uppercase pb-8">
        ALL PLANS INCLUDE AUTOMATED UPLOAD AND IST SCHEDULING. TAXES APPLICABLE AS PER REGIONAL DIRECTIVES.
      </div>
    </div>
  );
}
