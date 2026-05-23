"use client";

import { useState } from "react";
import { Clock, Plus, X, Trash2, ShieldAlert } from "lucide-react";

const HOURS = Array.from({ length: 18 }, (_, i) => `${(i + 6).toString().padStart(2, "0")}:00`);

export default function SettingsPage() {
  // Section 2: Schedule State
  const [videosPerDay, setVideosPerDay] = useState(3);
  const [uploadTimes, setUploadTimes] = useState(["09:00", "15:00", "20:00"]);

  // Section 3: Topics State
  const [topics, setTopics] = useState(["AI", "Machine Learning", "Automation", "Coding", "Robots"]);
  const [isAddingTopic, setIsAddingTopic] = useState(false);
  const [customTopic, setCustomTopic] = useState("");

  // Section 4: Characters State
  const [characters, setCharacters] = useState([
    { id: 1, name: "NEXUS", role: "EXPLAINER", voice: "en-US-Journey-D" },
    { id: 2, name: "AURA", role: "EXPLAINER", voice: "en-US-Journey-F" },
    { id: 3, name: "VORTEX", role: "ANALYST", voice: "en-GB-Standard-A" },
  ]);

  const handleVideosChange = (num: number) => {
    setVideosPerDay(num);
    const defaultTimes = ["09:00", "15:00", "20:00"];
    setUploadTimes(defaultTimes.slice(0, num));
  };

  const handleTimeChange = (index: number, newTime: string) => {
    const newTimes = [...uploadTimes];
    newTimes[index] = newTime;
    setUploadTimes(newTimes);
  };

  const handleAddTopic = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && customTopic.trim()) {
      if (!topics.includes(customTopic.trim())) setTopics([...topics, customTopic.trim()]);
      setCustomTopic("");
      setIsAddingTopic(false);
    }
  };

  const handleRemoveTopic = (topicToRemove: string) => {
    setTopics(topics.filter((t) => t !== topicToRemove));
  };

  const handleRemoveCharacter = (id: number) => {
    setCharacters(characters.filter((c) => c.id !== id));
  };

  const Divider = () => <div className="border-t-2 border-cronus-red my-12" />;

  return (
    <div className="max-w-4xl mx-auto pb-24">
      <h1 className="font-sans font-bold text-5xl uppercase mb-12 text-cronus-white">
        SETTINGS<span className="text-cronus-red">_</span>
      </h1>

      {/* SECTION 1 — YouTube Connection */}
      <section>
        <h2 className="font-mono text-xl uppercase mb-6 text-cronus-white">01. YouTube Connection</h2>
        <div className="border-2 border-cronus-gray/30 border-l-8 border-l-cronus-red bg-cronus-surface p-6 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div>
            <div className="font-mono text-sm uppercase tracking-widest text-cronus-gray mb-1">Connected Channel</div>
            <div className="font-sans font-bold text-2xl text-cronus-white uppercase mb-2">INDUSTRIAL_LOGS</div>
            <div className="flex gap-4 font-mono text-xs text-cronus-gray">
              <span>Subscribers: 12.4K</span>
              <span>•</span>
              <span>Connected on: May 17 2026</span>
            </div>
          </div>
          <button
            onClick={() => console.log("Disconnecting YouTube...")}
            className="px-6 py-3 font-sans font-bold text-lg uppercase border-2 border-cronus-white text-cronus-white hover:border-cronus-red hover:text-cronus-red transition-colors whitespace-nowrap"
          >
            DISCONNECT
          </button>
        </div>
      </section>

      <Divider />

      {/* SECTION 2 — Schedule */}
      <section>
        <h2 className="font-mono text-xl uppercase mb-6 text-cronus-white">02. Schedule</h2>
        <div className="border-2 border-cronus-gray/30 bg-cronus-surface p-6">
          <div className="mb-8">
            <div className="font-mono text-sm uppercase tracking-widest text-cronus-gray mb-4">Output Volume</div>
            <div className="flex gap-4">
              {[1, 2, 3].map((num) => (
                <button
                  key={num}
                  onClick={() => handleVideosChange(num)}
                  className={`w-14 h-14 flex items-center justify-center font-sans font-bold text-xl border-2 transition-all ${
                    videosPerDay === num
                      ? "bg-cronus-red border-cronus-red text-cronus-bg shadow-[4px_4px_0px_0px_rgba(255,34,0,0.3)]"
                      : "bg-cronus-bg border-cronus-gray text-cronus-white hover:border-cronus-white"
                  }`}
                >
                  {num}
                </button>
              ))}
            </div>
          </div>

          <div className="mb-8">
            <div className="font-mono text-sm uppercase tracking-widest text-cronus-gray mb-4">Upload Times</div>
            <div className="flex flex-col gap-4 max-w-sm">
              {Array.from({ length: videosPerDay }).map((_, index) => (
                <div key={index} className="flex items-center">
                  <div className="w-10 h-10 bg-cronus-gray/20 flex items-center justify-center mr-4 font-mono text-sm text-cronus-white border-2 border-cronus-gray/30">
                    {index + 1}
                  </div>
                  <div className="relative flex-1">
                    <Clock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-cronus-gray" />
                    <select
                      value={uploadTimes[index]}
                      onChange={(e) => handleTimeChange(index, e.target.value)}
                      className="w-full bg-cronus-bg border-2 border-cronus-gray/30 text-cronus-white pl-10 pr-4 py-2 font-mono text-sm uppercase appearance-none focus:outline-none focus:border-cronus-red transition-colors cursor-pointer"
                    >
                      {HOURS.map((hour) => <option key={hour} value={hour}>{hour}</option>)}
                    </select>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <button
            onClick={() => console.log("Saving schedule...", { videosPerDay, uploadTimes })}
            className="w-full md:w-auto px-8 py-4 font-sans font-bold text-lg uppercase bg-cronus-red text-cronus-bg hover:bg-cronus-white transition-colors"
          >
            SAVE SCHEDULE
          </button>
        </div>
      </section>

      <Divider />

      {/* SECTION 3 — Topics */}
      <section>
        <h2 className="font-mono text-xl uppercase mb-6 text-cronus-white">03. Topics</h2>
        <div className="border-2 border-cronus-gray/30 bg-cronus-surface p-6">
          <div className="flex flex-wrap gap-4 items-center mb-8">
            {topics.map((topic) => (
              <div key={topic} className="flex items-center border-2 border-cronus-white bg-cronus-bg px-4 py-2 font-mono text-sm uppercase">
                {topic}
                <button onClick={() => handleRemoveTopic(topic)} className="ml-3 text-cronus-red hover:text-white transition-colors">
                  <X className="w-4 h-4" />
                </button>
              </div>
            ))}
            {isAddingTopic ? (
              <input
                type="text" autoFocus value={customTopic} onChange={(e) => setCustomTopic(e.target.value)} onKeyDown={handleAddTopic}
                onBlur={() => { if (!customTopic) setIsAddingTopic(false); }}
                className="border-2 border-cronus-red border-dashed bg-cronus-bg text-cronus-white px-4 py-2 font-mono text-sm uppercase outline-none focus:border-solid"
                placeholder="TYPE & PRESS ENTER"
              />
            ) : (
              <button onClick={() => setIsAddingTopic(true)} className="flex items-center border-2 border-cronus-red border-dashed text-cronus-red hover:bg-cronus-red hover:text-cronus-bg hover:border-solid transition-all px-4 py-2 font-mono text-sm uppercase font-bold">
                <Plus className="w-4 h-4 mr-2" /> ADD TOPIC
              </button>
            )}
          </div>
          <button
            onClick={() => console.log("Saving topics...", { topics })}
            className="w-full md:w-auto px-8 py-4 font-sans font-bold text-lg uppercase bg-cronus-red text-cronus-bg hover:bg-cronus-white transition-colors"
          >
            SAVE TOPICS
          </button>
        </div>
      </section>

      <Divider />

      {/* SECTION 4 — Characters */}
      <section>
        <h2 className="font-mono text-xl uppercase mb-6 text-cronus-white">04. Characters</h2>
        <div className="border-2 border-cronus-gray/30 bg-cronus-surface p-6">
          <div className="space-y-4 mb-8">
            {characters.map((char) => (
              <div key={char.id} className="flex flex-col md:flex-row md:items-center justify-between border-2 border-cronus-gray/30 bg-cronus-bg p-4 gap-4">
                <div className="flex items-center gap-6">
                  <span className="font-sans font-bold text-lg text-cronus-white">{char.name}</span>
                  <span className="bg-cronus-white text-cronus-bg font-mono text-[10px] px-2 py-1 uppercase tracking-widest font-bold">
                    {char.role}
                  </span>
                  <span className="font-mono text-xs text-cronus-gray uppercase">VOICE: {char.voice}</span>
                </div>
                <button
                  onClick={() => handleRemoveCharacter(char.id)}
                  className="font-mono text-sm uppercase text-cronus-gray hover:text-cronus-red transition-colors flex items-center"
                >
                  <X className="w-4 h-4 mr-1" /> REMOVE
                </button>
              </div>
            ))}
          </div>
          <button
            onClick={() => console.log("Opening add character modal...")}
            className="w-full flex items-center justify-center border-2 border-cronus-red border-dashed text-cronus-red hover:bg-cronus-red hover:text-cronus-bg hover:border-solid transition-all py-4 font-sans font-bold text-lg uppercase mb-8"
          >
            <Plus className="w-5 h-5 mr-2" /> ADD CHARACTER
          </button>
          <button
            onClick={() => console.log("Saving characters...", { characters })}
            className="w-full md:w-auto px-8 py-4 font-sans font-bold text-lg uppercase bg-cronus-red text-cronus-bg hover:bg-cronus-white transition-colors"
          >
            SAVE CHARACTERS
          </button>
        </div>
      </section>

      <Divider />

      {/* SECTION 5 — Danger Zone */}
      <section>
        <div className="border-4 border-cronus-red bg-cronus-bg p-8 relative mt-12">
          <div className="absolute -top-4 left-6 bg-cronus-bg px-4 flex items-center text-cronus-red font-sans font-bold text-xl uppercase tracking-widest">
            <ShieldAlert className="w-6 h-6 mr-2" /> DANGER ZONE
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mt-6">
            <div>
              <button
                onClick={() => console.log("Deleting all history...")}
                className="w-full flex items-center justify-center px-6 py-4 border-2 border-cronus-red text-cronus-red hover:bg-cronus-red hover:text-cronus-bg font-sans font-bold text-lg uppercase transition-colors mb-3"
              >
                <Trash2 className="w-5 h-5 mr-3" /> DELETE ALL HISTORY
              </button>
              <p className="font-mono text-xs text-cronus-gray/60 leading-relaxed max-w-sm">
                Permanently removes all generated logs, video records, and history entries. Cannot be undone.
              </p>
            </div>

            <div>
              <button
                onClick={() => console.log("Deactivating agent...")}
                className="w-full flex items-center justify-center px-6 py-4 border-2 border-cronus-red text-cronus-red hover:bg-cronus-red hover:text-cronus-bg font-sans font-bold text-lg uppercase transition-colors mb-3"
              >
                DEACTIVATE AGENT
              </button>
              <p className="font-mono text-xs text-cronus-gray/60 leading-relaxed max-w-sm">
                Halts all current and scheduled operations immediately. Requires manual restart to resume automation.
              </p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
