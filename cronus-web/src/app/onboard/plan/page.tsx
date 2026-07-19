"use client";

import { useState } from "react";

import { PricingPlans } from "@/components/pricing-plans";

export default function OnboardPlanPage() {

  const [loadingPlan, setLoadingPlan] = useState<string | null>(null);

  const handlePlanSelect = async (planType: string) => {
    setLoadingPlan(planType);
    try {
      if (["daily", "weekly", "monthly", "pro"].includes(planType)) {
        const res = await fetch("/api/payments/create-checkout", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ planType, returnUrl: window.location.origin }),
        });
        const data = await res.json();
        if (data.url) {
          window.location.href = data.url;
          return;
        } else {
          throw new Error(data.error || "Failed to create checkout session");
        }
      }

      const res = await fetch("/api/plans/update", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ planType }),
      });

      if (!res.ok) {
        throw new Error("Failed to update plan");
      }

      // Full page load to bypass Next.js router cache
      window.location.href = "/onboard/youtube";
    } catch (err) {
      console.error(err);
      setLoadingPlan(null);
    }
  };

  return (
    <div className="min-h-screen bg-cronus-bg flex flex-col items-center pt-24 px-6">
      <PricingPlans onPlanSelect={handlePlanSelect} loadingPlan={loadingPlan} />
    </div>
  );
}
