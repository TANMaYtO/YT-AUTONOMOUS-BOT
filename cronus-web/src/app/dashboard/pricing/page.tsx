"use client";

import { useState } from "react";
import { PricingPlans } from "@/components/pricing-plans";

export default function DashboardPricingPage() {
  const [loadingPlan, setLoadingPlan] = useState<string | null>(null);

  const handlePlanSelect = async (planType: string) => {
    setLoadingPlan(planType);
    try {
      if (planType === "pro") {
        // Trigger Stripe Checkout
        const res = await fetch("/api/payments/create-checkout", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ returnUrl: window.location.origin }),
        });
        const data = await res.json();
        if (data.url) {
          window.location.href = data.url;
          return;
        } else {
          throw new Error(data.error || "Failed to create checkout session");
        }
      }

      // Free plan downgrade/selection
      const res = await fetch("/api/plans/update", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ planType }),
      });

      if (!res.ok) {
        throw new Error("Failed to update plan");
      }
      
      setLoadingPlan(null);
      window.location.reload();
    } catch (err) {
      console.error(err);
      setLoadingPlan(null);
    }
  };

  return (
    <div className="w-full h-full pt-8">
      <PricingPlans onPlanSelect={handlePlanSelect} loadingPlan={loadingPlan} />
    </div>
  );
}
