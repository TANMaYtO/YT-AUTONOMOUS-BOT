import { Check } from "lucide-react";

interface ProgressBarProps {
  currentStep: 1 | 2 | 3;
}

export function ProgressBar({ currentStep }: ProgressBarProps) {
  return (
    <div className="w-full border-b-2 border-cronus-gray/30 bg-cronus-surface py-4 px-8 flex justify-center items-center space-x-4 md:space-x-8 font-mono text-xs uppercase tracking-widest">
      {/* STEP 1 */}
      <div className={`flex items-center ${currentStep === 1 ? "text-cronus-red font-bold" : currentStep > 1 ? "text-cronus-white" : "text-cronus-gray"}`}>
        <span className="mr-2">
          {currentStep > 1 ? <Check className="w-4 h-4 text-green-500" /> : "[01]"}
        </span>
        YOUTUBE {currentStep === 1 && <span className="ml-2 animate-pulse">_</span>}
      </div>

      <div className="text-cronus-gray/30">{"//"}</div>

      {/* STEP 2 */}
      <div className={`flex items-center ${currentStep === 2 ? "text-cronus-red font-bold" : currentStep > 2 ? "text-cronus-white" : "text-cronus-gray"}`}>
        <span className="mr-2">
          {currentStep > 2 ? <Check className="w-4 h-4 text-green-500" /> : "[02]"}
        </span>
        NICHE {currentStep === 2 && <span className="ml-2 animate-pulse">_</span>}
      </div>

      <div className="text-cronus-gray/30">{"//"}</div>

      {/* STEP 3 */}
      <div className={`flex items-center ${currentStep === 3 ? "text-cronus-red font-bold" : "text-cronus-gray"}`}>
        <span className="mr-2">[03]</span>
        SCHEDULE {currentStep === 3 && <span className="ml-2 animate-pulse">_</span>}
      </div>
    </div>
  );
}
