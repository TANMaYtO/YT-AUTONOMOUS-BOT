"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { ProgressBar } from "@/components/onboard/progress-bar";
import { ArrowRight, X, Plus } from "lucide-react";

const NICHES = [
  "TECH & AI",
  "ANIME",
  "FINANCE",
  "GAMING",
  "SCIENCE",
  "HISTORY",
  "CUSTOM",
];

const DEFAULT_TOPICS: Record<string, string[]> = {
  "TECH & AI": ["AI", "Machine Learning", "Automation", "Coding", "Robots"],
  "ANIME": ["One Piece", "Jujutsu Kaisen", "Attack on Titan", "Naruto", "Bleach"],
  "FINANCE": ["Crypto", "Investing", "Stock Market", "Economy", "Real Estate"],
  "GAMING": ["Elden Ring", "Minecraft", "GTA 6", "Esports", "Indie Games"],
  "SCIENCE": ["Space", "Physics", "Biology", "Quantum Mechanics", "Astronomy"],
  "HISTORY": ["Ancient Rome", "WWII", "Empires", "Mythology", "Cold War"],
  "CUSTOM": [],
};

const CHARACTERS = [
  { name: "NEXUS", role: "EXPLAINER" },
  { name: "AURA", role: "EXPLAINER" },
  { name: "VORTEX", role: "ANALYST" },
  { name: "ECHO", role: "NARRATOR" },
  { name: "PULSE", role: "COMMENTATOR" },
];

export default function NicheStep() {
  const router = useRouter();
  const [selectedNiche, setSelectedNiche] = useState("TECH & AI");
  const [topics, setTopics] = useState<string[]>(DEFAULT_TOPICS["TECH & AI"]);
  const [customTopic, setCustomTopic] = useState("");
  const [isAddingTopic, setIsAddingTopic] = useState(false);
  const [selectedCharacter, setSelectedCharacter] = useState("NEXUS");

  // Update topics when niche changes
  useEffect(() => {
    setTopics(DEFAULT_TOPICS[selectedNiche] || []);
    setIsAddingTopic(false);
  }, [selectedNiche]);

  const removeTopic = (topicToRemove: string) => {
    setTopics(topics.filter((t) => t !== topicToRemove));
  };

  const addTopic = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && customTopic.trim()) {
      if (!topics.includes(customTopic.trim())) {
        setTopics([...topics, customTopic.trim()]);
      }
      setCustomTopic("");
      setIsAddingTopic(false);
    }
  };

  const [isLoading, setIsLoading] = useState(false);

  const handleContinue = async () => {
    setIsLoading(true);
    try {
      const res = await fetch("/api/configs/update", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          niche: selectedNiche,
          topics: topics,
          characters: [selectedCharacter],
        }),
      });

      if (!res.ok) throw new Error("Failed to save config");
      
      // Full page load to avoid Next.js router cache issues
      window.location.href = "/onboard/schedule";
    } catch (err) {
      console.error(err);
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-cronus-bg flex flex-col items-center">
      <ProgressBar currentStep={2} />

      <main className="flex-1 w-full max-w-5xl mx-auto flex flex-col p-6 py-12">
        <h1 className="font-sans font-bold text-5xl uppercase mb-12 text-cronus-white text-center">
          DEFINE CONTENT
          <span className="text-cronus-red">_</span>
        </h1>

        {/* Niche Selector */}
        <section className="mb-12">
          <h2 className="font-mono text-xl uppercase mb-4 text-cronus-white border-b-2 border-cronus-gray/30 pb-2">01. Select Niche</h2>
          <div className="flex flex-wrap gap-4">
            {NICHES.map((niche) => (
              <button
                key={niche}
                onClick={() => setSelectedNiche(niche)}
                className={`px-6 py-3 font-mono text-sm uppercase transition-all border-2 ${
                  selectedNiche === niche
                    ? "bg-cronus-red border-cronus-red text-cronus-bg font-bold shadow-[4px_4px_0px_0px_rgba(255,34,0,0.3)]"
                    : "border-cronus-gray text-cronus-white hover:border-cronus-white hover:text-cronus-white"
                }`}
              >
                {niche}
              </button>
            ))}
          </div>
        </section>

        {/* Topics */}
        <section className="mb-12">
          <h2 className="font-mono text-xl uppercase mb-4 text-cronus-white border-b-2 border-cronus-gray/30 pb-2">02. Core Topics</h2>
          <div className="flex flex-wrap gap-4 items-center">
            {topics.map((topic) => (
              <div key={topic} className="flex items-center border-2 border-cronus-white bg-cronus-surface px-4 py-2 font-mono text-sm uppercase">
                {topic}
                <button onClick={() => removeTopic(topic)} className="ml-3 text-cronus-red hover:text-white transition-colors">
                  <X className="w-4 h-4" />
                </button>
              </div>
            ))}

            {isAddingTopic ? (
              <input
                type="text"
                autoFocus
                value={customTopic}
                onChange={(e) => setCustomTopic(e.target.value)}
                onKeyDown={addTopic}
                onBlur={() => {
                  if (!customTopic) setIsAddingTopic(false);
                }}
                className="border-2 border-cronus-red border-dashed bg-cronus-bg text-cronus-white px-4 py-2 font-mono text-sm uppercase outline-none focus:border-solid"
                placeholder="TYPE & PRESS ENTER"
              />
            ) : (
              <button
                onClick={() => setIsAddingTopic(true)}
                className="flex items-center border-2 border-cronus-red border-dashed text-cronus-red hover:bg-cronus-red hover:text-cronus-bg hover:border-solid transition-all px-4 py-2 font-mono text-sm uppercase font-bold"
              >
                <Plus className="w-4 h-4 mr-2" /> ADD CUSTOM TOPIC
              </button>
            )}
          </div>
        </section>

        {/* Characters */}
        <section className="mb-16">
          <h2 className="font-mono text-xl uppercase mb-4 text-cronus-white border-b-2 border-cronus-gray/30 pb-2">03. Primary Character</h2>
          <div className="flex overflow-x-auto gap-6 pb-4 scrollbar-hide">
            {CHARACTERS.map((char) => (
              <button
                key={char.name}
                onClick={() => setSelectedCharacter(char.name)}
                className={`min-w-[200px] border-2 text-left transition-all group ${
                  selectedCharacter === char.name
                    ? "border-cronus-red bg-cronus-red/5 shadow-[4px_4px_0px_0px_rgba(255,34,0,0.3)]"
                    : "border-cronus-gray/30 bg-cronus-surface hover:border-cronus-gray"
                }`}
              >
                <div className="h-32 bg-cronus-gray/10 border-b-2 border-cronus-gray/30 flex items-center justify-center mb-2 group-hover:bg-cronus-gray/20 transition-colors">
                  <span className="font-mono text-2xl font-bold text-cronus-gray/40">
                    {char.name.charAt(0)}
                  </span>
                </div>
                <div className="p-4 pt-2">
                  <h3 className="font-sans font-bold text-xl text-cronus-white">{char.name}</h3>
                  <span className="inline-block mt-2 bg-cronus-white text-cronus-bg font-mono text-[10px] px-2 py-1 uppercase tracking-widest font-bold">
                    {char.role}
                  </span>
                </div>
              </button>
            ))}
          </div>
        </section>

        <div className="flex justify-center">
          <button
            onClick={handleContinue}
            disabled={isLoading}
            className="w-full max-w-md flex items-center justify-center font-sans font-bold text-xl uppercase px-8 py-4 bg-cronus-red text-cronus-white border-2 border-cronus-red hover:bg-cronus-bg hover:text-cronus-red transition-all shadow-[8px_8px_0px_0px_rgba(255,34,0,0.3)] hover:shadow-none hover:translate-x-2 hover:translate-y-2 disabled:opacity-50 disabled:hover:translate-x-0 disabled:hover:translate-y-0 disabled:hover:shadow-[8px_8px_0px_0px_rgba(255,34,0,0.3)]"
          >
            {isLoading ? "SAVING..." : "CONTINUE"} <ArrowRight className="ml-3 w-6 h-6" />
          </button>
        </div>
      </main>
    </div>
  );
}
