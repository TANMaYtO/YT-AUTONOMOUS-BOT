"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { PricingPlans } from "@/components/pricing-plans";

export default function OnboardPlanPage() {
  const router = useRouter();
  const [loadingPlan, setLoadingPlan] = useState<string | null>(null);

  const handlePlanSelect = async (planType: string) => {
    setLoadingPlan(planType);
    try {
      const res = await fetch("/api/plans/update", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ planType }),
      });

      if (!res.ok) {
        throw new Error("Failed to update plan");
      }

      router.push("/onboard/youtube");
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
