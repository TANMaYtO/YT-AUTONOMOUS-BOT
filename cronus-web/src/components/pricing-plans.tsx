"use client";

import { Check, Zap } from "lucide-react";

interface PricingPlansProps {
  onPlanSelect: (planType: string) => Promise<void>;
  loadingPlan?: string | null;
}

export function PricingPlans({ onPlanSelect, loadingPlan }: PricingPlansProps) {
  return (
    <div className="w-full max-w-7xl mx-auto flex flex-col h-full py-6">
      <div className="mb-10 text-center md:text-left">
        <div className="font-mono text-cronus-red text-sm uppercase tracking-widest font-bold mb-2 flex items-center justify-center md:justify-start">
          <Zap className="w-4 h-4 mr-2 text-cronus-red animate-pulse" /> SELECT_SYSTEM_CAPACITY (ALL USD $)
        </div>
        <h1 className="font-sans font-bold text-4xl md:text-5xl uppercase text-cronus-white">
          CRONUS / SUBSCRIPTION_TIERS
        </h1>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8 flex-1 border-t-2 border-cronus-red pt-10">
        {/* Tier 1: Daily Pass */}
        <div className="flex flex-col border-2 border-cronus-gray/30 bg-cronus-bg p-6 hover:border-cronus-white transition-all">
          <div className="mb-6">
            <div className="font-mono text-xs text-cronus-gray uppercase tracking-widest mb-1">
              [TIER_01]
            </div>
            <h2 className="font-sans font-bold text-2xl text-cronus-white uppercase mb-4">
              DAILY_PASS
            </h2>
            <div className="flex items-baseline text-cronus-white font-sans font-bold">
              <span className="text-5xl tracking-tighter">$1</span>
              <span className="text-sm font-mono text-cronus-gray ml-2">/ day</span>
            </div>
          </div>
          
          <div className="border-t border-cronus-gray/30 mb-6"></div>

          <ul className="space-y-3 mb-8 flex-1 font-sans text-sm text-cronus-white">
            <li className="flex items-center">
              <Check className="w-4 h-4 text-cronus-red mr-3 shrink-0" strokeWidth={3} />
              1 Video / 24 Hours
            </li>
            <li className="flex items-center">
              <Check className="w-4 h-4 text-cronus-red mr-3 shrink-0" strokeWidth={3} />
              Kokoro AI Voice Engine
            </li>
            <li className="flex items-center">
              <Check className="w-4 h-4 text-cronus-red mr-3 shrink-0" strokeWidth={3} />
              Automated YouTube Upload
            </li>
            <li className="flex items-center">
              <Check className="w-4 h-4 text-cronus-red mr-3 shrink-0" strokeWidth={3} />
              No Watermark
            </li>
          </ul>

          <button
            onClick={() => onPlanSelect("daily")}
            disabled={!!loadingPlan}
            className="w-full py-4 font-mono text-xs font-bold text-cronus-white border-2 border-cronus-white hover:bg-cronus-white hover:text-cronus-bg transition-colors uppercase tracking-widest disabled:opacity-50"
          >
            {loadingPlan === "daily" ? "[PROCESSING...]" : "[SELECT_DAILY]"}
          </button>
        </div>

        {/* Tier 2: Weekly Pass */}
        <div className="flex flex-col border-2 border-cronus-gray/30 bg-cronus-bg p-6 hover:border-cronus-white transition-all">
          <div className="mb-6">
            <div className="font-mono text-xs text-cronus-red uppercase tracking-widest mb-1">
              [TIER_02 / VALUE]
            </div>
            <h2 className="font-sans font-bold text-2xl text-cronus-white uppercase mb-4">
              WEEKLY_PASS
            </h2>
            <div className="flex items-baseline text-cronus-white font-sans font-bold">
              <span className="text-5xl tracking-tighter">$5</span>
              <span className="text-sm font-mono text-cronus-gray ml-2">/ week</span>
            </div>
          </div>
          
          <div className="border-t border-cronus-gray/30 mb-6"></div>

          <ul className="space-y-3 mb-8 flex-1 font-sans text-sm text-cronus-white">
            <li className="flex items-center">
              <Check className="w-4 h-4 text-cronus-red mr-3 shrink-0" strokeWidth={3} />
              3 Videos / Day (21 Total)
            </li>
            <li className="flex items-center">
              <Check className="w-4 h-4 text-cronus-red mr-3 shrink-0" strokeWidth={3} />
              Premium Anime Characters
            </li>
            <li className="flex items-center">
              <Check className="w-4 h-4 text-cronus-red mr-3 shrink-0" strokeWidth={3} />
              Priority Rendering Queue
            </li>
            <li className="flex items-center">
              <Check className="w-4 h-4 text-cronus-red mr-3 shrink-0" strokeWidth={3} />
              Custom Upload Time Slots
            </li>
          </ul>

          <button
            onClick={() => onPlanSelect("weekly")}
            disabled={!!loadingPlan}
            className="w-full py-4 font-mono text-xs font-bold text-cronus-white border-2 border-cronus-white hover:bg-cronus-white hover:text-cronus-bg transition-colors uppercase tracking-widest disabled:opacity-50"
          >
            {loadingPlan === "weekly" ? "[PROCESSING...]" : "[SELECT_WEEKLY]"}
          </button>
        </div>

        {/* Tier 3: Monthly Industrial */}
        <div className="flex flex-col relative border-2 border-cronus-red bg-cronus-bg p-6 shadow-[8px_8px_0px_0px_rgba(255,34,0,0.3)] md:-mt-4">
          <div className="absolute top-0 right-0 bg-cronus-red text-cronus-white font-mono text-[10px] font-bold uppercase px-3 py-1 tracking-widest">
            BEST_VALUE / INDUSTRIAL
          </div>
          <div className="mb-6 mt-2">
            <div className="font-mono text-xs text-cronus-red uppercase tracking-widest mb-1">
              [TIER_03 / MAX_OUTPUT]
            </div>
            <h2 className="font-sans font-bold text-2xl text-cronus-white uppercase mb-4">
              MONTHLY_PASS
            </h2>
            <div className="flex items-baseline text-cronus-red font-sans font-bold">
              <span className="text-5xl tracking-tighter">$25</span>
              <span className="text-sm font-mono text-cronus-gray ml-2">/ month</span>
            </div>
          </div>
          
          <div className="border-t-2 border-cronus-red mb-6"></div>

          <ul className="space-y-3 mb-8 flex-1 font-sans text-sm text-cronus-white">
            <li className="flex items-center">
              <Check className="w-4 h-4 text-cronus-red mr-3 shrink-0" strokeWidth={3} />
              5 Videos / Day (150+ / mo)
            </li>
            <li className="flex items-center">
              <Check className="w-4 h-4 text-cronus-red mr-3 shrink-0" strokeWidth={3} />
              All Custom Characters & Voices
            </li>
            <li className="flex items-center">
              <Check className="w-4 h-4 text-cronus-red mr-3 shrink-0" strokeWidth={3} />
              Cloudflare R2 Object Storage
            </li>
            <li className="flex items-center">
              <Check className="w-4 h-4 text-cronus-red mr-3 shrink-0" strokeWidth={3} />
              Dedicated 24/7 VIP Scheduler
            </li>
          </ul>

          <button
            onClick={() => onPlanSelect("monthly")}
            disabled={!!loadingPlan}
            className="w-full py-4 bg-cronus-red text-cronus-white font-mono text-xs font-bold uppercase hover:bg-cronus-white hover:text-cronus-bg transition-colors tracking-widest disabled:opacity-50 shadow-[4px_4px_0px_0px_rgba(255,255,255,0.1)]"
          >
            {loadingPlan === "monthly" ? "[PROCESSING...]" : "[SELECT_MONTHLY]"}
          </button>
        </div>
      </div>

      <div className="mt-12 pt-6 border-t border-cronus-gray/30 text-center font-mono text-[10px] text-cronus-gray tracking-widest uppercase pb-6">
        ALL PLANS CONNECT DIRECTLY TO SHOPIFY IN USD ($). INSTANT ACTIVATION UPON PAYMENT CONFIRMATION.
      </div>
    </div>
  );
}
