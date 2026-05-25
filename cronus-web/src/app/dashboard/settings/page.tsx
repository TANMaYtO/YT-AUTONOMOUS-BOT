"use client";

import { useState, useEffect } from "react";
import { Clock, Plus, X, Trash2, ShieldAlert, Lock } from "lucide-react";
import { createClient } from "@/lib/supabase/client";

const HOURS = Array.from({ length: 18 }, (_, i) => `${(i + 6).toString().padStart(2, "0")}:00`);

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface YouTubeConnection {
  channel_id: string;
  channel_name: string;
  subscriber_count: number;
  connected_at: string;
}

interface Character {
  id: number;
  name: string;
  role: string;
  voice: string;
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function SettingsPage(): JSX.Element {
  /** Root settings page — wired to Supabase for all five sections. */

  const supabase = createClient();

  // Global UI state
  const [loading, setLoading] = useState<boolean>(true);
  const [savedLabel, setSavedLabel] = useState<string | null>(null);

  // Section 1: YouTube Connection
  const [ytConnection, setYtConnection] = useState<YouTubeConnection | null>(null);

  // Section 2: Schedule
  const [videosPerDay, setVideosPerDay] = useState<number>(1);
  const [uploadTimes, setUploadTimes] = useState<string[]>(["09:00"]);
  const [isPro, setIsPro] = useState<boolean>(false);

  // Section 3: Topics
  const [topics, setTopics] = useState<string[]>([]);
  const [isAddingTopic, setIsAddingTopic] = useState<boolean>(false);
  const [customTopic, setCustomTopic] = useState<string>("");

  // Section 4: Characters
  const [characters, setCharacters] = useState<Character[]>([]);

  /* ---------------------------------------------------------------- */
  /*  Flash a "SAVED" badge for 2 seconds                             */
  /* ---------------------------------------------------------------- */

  function flashSaved(label: string): void {
    /** Show a brief success toast that auto-dismisses. */
    setSavedLabel(label);
    setTimeout(() => setSavedLabel(null), 2000);
  }

  /* ---------------------------------------------------------------- */
  /*  Initial data fetch                                               */
  /* ---------------------------------------------------------------- */

  useEffect(() => {
    /** Fetch all settings data from Supabase on mount. */
    async function fetchAll(): Promise<void> {
      const {
        data: { user },
      } = await supabase.auth.getUser();
      if (!user) return;

      // Parallel fetches
      const [ytRes, configRes, planRes] = await Promise.all([
        supabase
          .from("youtube_connections")
          .select("channel_id, channel_name, subscriber_count, connected_at")
          .eq("user_id", user.id)
          .maybeSingle(),
        supabase
          .from("user_configs")
          .select("videos_per_day, upload_times, topics, characters")
          .eq("user_id", user.id)
          .single(),
        supabase
          .from("plans")
          .select("plan_type")
          .eq("user_id", user.id)
          .single(),
      ]);

      // YouTube
      if (ytRes.data) setYtConnection(ytRes.data as YouTubeConnection);

      // Plan
      const proUser = planRes.data?.plan_type === "pro";
      setIsPro(proUser);

      // Config
      if (configRes.data) {
        const cfg = configRes.data;
        setVideosPerDay(cfg.videos_per_day ?? 1);
        setUploadTimes((cfg.upload_times as string[]) ?? ["09:00"]);
        setTopics((cfg.topics as string[]) ?? []);
        setCharacters((cfg.characters as Character[]) ?? []);
      }

      setLoading(false);
    }

    fetchAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /* ---------------------------------------------------------------- */
  /*  Section 1 handlers                                               */
  /* ---------------------------------------------------------------- */

  async function handleDisconnectYouTube(): Promise<void> {
    /** Delete the YouTube connection after user confirmation. */
    const confirmed = window.confirm(
      "Are you sure you want to disconnect your YouTube channel? You will need to reconnect to resume uploads."
    );
    if (!confirmed) return;

    const {
      data: { user },
    } = await supabase.auth.getUser();
    if (!user) return;

    const { error } = await supabase
      .from("youtube_connections")
      .delete()
      .eq("user_id", user.id);

    if (!error) {
      setYtConnection(null);
      flashSaved("DISCONNECTED");
    }
  }

  /* ---------------------------------------------------------------- */
  /*  Section 2 handlers                                               */
  /* ---------------------------------------------------------------- */

  function handleVideosChange(num: number): void {
    /** Update video count — blocked for free users above 1. */
    if (!isPro && num > 1) return;
    setVideosPerDay(num);
    const defaultTimes = ["09:00", "15:00", "20:00"];
    setUploadTimes(defaultTimes.slice(0, num));
  }

  function handleTimeChange(index: number, newTime: string): void {
    /** Update a single upload time slot. */
    const newTimes = [...uploadTimes];
    newTimes[index] = newTime;
    setUploadTimes(newTimes);
  }

  async function handleSaveSchedule(): Promise<void> {
    /** Persist schedule changes via the config API. */
    const res = await fetch("/api/configs/update", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ videos_per_day: videosPerDay, upload_times: uploadTimes }),
    });
    if (res.ok) flashSaved("SCHEDULE SAVED");
  }

  /* ---------------------------------------------------------------- */
  /*  Section 3 handlers                                               */
  /* ---------------------------------------------------------------- */

  function handleAddTopic(e: React.KeyboardEvent<HTMLInputElement>): void {
    /** Add a custom topic on Enter key press. */
    if (e.key === "Enter" && customTopic.trim()) {
      if (!topics.includes(customTopic.trim())) setTopics([...topics, customTopic.trim()]);
      setCustomTopic("");
      setIsAddingTopic(false);
    }
  }

  function handleRemoveTopic(topicToRemove: string): void {
    /** Remove a topic from the local state. */
    setTopics(topics.filter((t) => t !== topicToRemove));
  }

  async function handleSaveTopics(): Promise<void> {
    /** Persist topic changes via the config API. */
    const res = await fetch("/api/configs/update", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topics }),
    });
    if (res.ok) flashSaved("TOPICS SAVED");
  }

  /* ---------------------------------------------------------------- */
  /*  Section 4 handlers                                               */
  /* ---------------------------------------------------------------- */

  function handleRemoveCharacter(id: number): void {
    /** Remove a character from local state by id. */
    setCharacters(characters.filter((c) => c.id !== id));
  }

  function handleAddCharacter(): void {
    /** Prompt user for a character name and add a stub to state. */
    const name = window.prompt("Enter character name:")?.trim().toUpperCase();
    if (!name) return;
    const newId = characters.length > 0 ? Math.max(...characters.map((c) => c.id)) + 1 : 1;
    setCharacters([
      ...characters,
      { id: newId, name, role: "EXPLAINER", voice: "en-US-Journey-D" },
    ]);
  }

  async function handleSaveCharacters(): Promise<void> {
    /** Persist character changes via the config API. */
    const res = await fetch("/api/configs/update", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ characters }),
    });
    if (res.ok) flashSaved("CHARACTERS SAVED");
  }

  /* ---------------------------------------------------------------- */
  /*  Section 5 handlers                                               */
  /* ---------------------------------------------------------------- */

  async function handleDeleteAllHistory(): Promise<void> {
    /** Delete all video records for the current user after confirmation. */
    const confirmed = window.confirm("Are you sure? This cannot be undone.");
    if (!confirmed) return;

    const {
      data: { user },
    } = await supabase.auth.getUser();
    if (!user) return;

    const { error } = await supabase
      .from("videos")
      .delete()
      .eq("user_id", user.id);

    if (!error) flashSaved("HISTORY DELETED");
  }

  async function handleDeactivateAgent(): Promise<void> {
    /** Deactivate the agent by setting is_active to false after confirmation. */
    const confirmed = window.confirm(
      "Are you sure you want to deactivate the agent? This will halt all scheduled operations."
    );
    if (!confirmed) return;

    const {
      data: { user },
    } = await supabase.auth.getUser();
    if (!user) return;

    const { error } = await supabase
      .from("user_configs")
      .update({ is_active: false })
      .eq("user_id", user.id);

    if (!error) flashSaved("AGENT DEACTIVATED");
  }

  /* ---------------------------------------------------------------- */
  /*  Shared UI                                                        */
  /* ---------------------------------------------------------------- */

  const Divider = (): JSX.Element => <div className="border-t-2 border-cronus-red my-12" />;

  /* ---------------------------------------------------------------- */
  /*  Loading screen                                                   */
  /* ---------------------------------------------------------------- */

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto pb-24 flex items-center justify-center min-h-[60vh]">
        <div className="font-mono text-cronus-gray uppercase tracking-widest animate-pulse">
          Loading settings...
        </div>
      </div>
    );
  }

  /* ---------------------------------------------------------------- */
  /*  Render                                                           */
  /* ---------------------------------------------------------------- */

  return (
    <div className="max-w-4xl mx-auto pb-24">
      {/* Saved toast */}
      {savedLabel && (
        <div className="fixed top-6 right-6 z-50 bg-cronus-red text-cronus-bg font-sans font-bold text-sm uppercase px-6 py-3 shadow-[4px_4px_0px_0px_rgba(255,34,0,0.3)] animate-pulse">
          ✓ {savedLabel}
        </div>
      )}

      <h1 className="font-sans font-bold text-5xl uppercase mb-12 text-cronus-white">
        SETTINGS<span className="text-cronus-red">_</span>
      </h1>

      {/* SECTION 1 — YouTube Connection */}
      <section>
        <h2 className="font-mono text-xl uppercase mb-6 text-cronus-white">01. YouTube Connection</h2>
        <div className="border-2 border-cronus-gray/30 border-l-8 border-l-cronus-red bg-cronus-surface p-6 flex flex-col md:flex-row md:items-center justify-between gap-6">
          {ytConnection ? (
            <>
              <div>
                <div className="font-mono text-sm uppercase tracking-widest text-cronus-gray mb-1">Connected Channel</div>
                <div className="font-sans font-bold text-2xl text-cronus-white uppercase mb-2">{ytConnection.channel_name}</div>
                <div className="flex gap-4 font-mono text-xs text-cronus-gray">
                  <span>Subscribers: {ytConnection.subscriber_count.toLocaleString()}</span>
                  <span>•</span>
                  <span>Connected on: {new Date(ytConnection.connected_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}</span>
                </div>
              </div>
              <button
                onClick={handleDisconnectYouTube}
                className="px-6 py-3 font-sans font-bold text-lg uppercase border-2 border-cronus-white text-cronus-white hover:border-cronus-red hover:text-cronus-red transition-colors whitespace-nowrap"
              >
                DISCONNECT
              </button>
            </>
          ) : (
            <div className="font-mono text-sm uppercase tracking-widest text-cronus-gray">
              No YouTube channel connected.
            </div>
          )}
        </div>
      </section>

      <Divider />

      {/* SECTION 2 — Schedule */}
      <section>
        <h2 className="font-mono text-xl uppercase mb-6 text-cronus-white">02. Schedule</h2>
        <div className="border-2 border-cronus-gray/30 bg-cronus-surface p-6">
          <div className="mb-8">
            <div className="font-mono text-sm uppercase tracking-widest text-cronus-gray mb-4">Output Volume</div>
            {isPro ? (
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
            ) : (
              <div className="flex items-center gap-6">
                <div className="w-14 h-14 flex items-center justify-center font-sans font-bold text-xl border-2 bg-cronus-red border-cronus-red text-cronus-bg shadow-[4px_4px_0px_0px_rgba(255,34,0,0.3)]">
                  1
                </div>
                <div className="flex flex-col">
                  <span className="font-mono text-sm text-cronus-white uppercase font-bold">1 Video / Day</span>
                  <span className="font-mono text-xs text-cronus-gray uppercase mt-1 flex items-center">
                    <Lock className="w-3 h-3 mr-1.5" />
                    Upgrade to PRO for up to 3 videos/day
                  </span>
                </div>
              </div>
            )}
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
            onClick={handleSaveSchedule}
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
            onClick={handleSaveTopics}
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
            onClick={handleAddCharacter}
            className="w-full flex items-center justify-center border-2 border-cronus-red border-dashed text-cronus-red hover:bg-cronus-red hover:text-cronus-bg hover:border-solid transition-all py-4 font-sans font-bold text-lg uppercase mb-8"
          >
            <Plus className="w-5 h-5 mr-2" /> ADD CHARACTER
          </button>
          <button
            onClick={handleSaveCharacters}
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
                onClick={handleDeleteAllHistory}
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
                onClick={handleDeactivateAgent}
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
