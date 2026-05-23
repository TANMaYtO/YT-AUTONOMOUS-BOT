"use client";

import { Activity, PlayCircle, Clock, AlertTriangle } from "lucide-react";

// Mock Data
const STATS = {
  totalVideos: 142,
  totalViews: "84.2K",
  uptime: "99.9%",
};

const QUEUE = [
  {
    id: "vid-001",
    title: "Why AI will replace coders by 2028",
    topic: "AI",
    scheduled: "15:00 IST",
    status: "ASSEMBLING",
  },
  {
    id: "vid-002",
    title: "Top 5 VS Code Extensions",
    topic: "Coding",
    scheduled: "20:00 IST",
    status: "PENDING",
  },
];

const HISTORY = [
  {
    id: "run-982",
    title: "React vs Vue in 2026",
    characters: "NEXUS x VORTEX",
    topic: "Web Dev",
    status: "UPLOADED",
    date: "Today, 09:00 IST",
  },
  {
    id: "run-981",
    title: "Next.js App Router explained",
    characters: "AURA x ECHO",
    topic: "Next.js",
    status: "UPLOADED",
    date: "Yesterday, 20:00 IST",
  },
  {
    id: "run-980",
    title: "Tailwind CSS Secrets",
    characters: "PULSE",
    topic: "CSS",
    status: "FAILED",
    date: "Yesterday, 15:00 IST",
  },
];

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      {/* Stats Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="border-2 border-cronus-gray/30 p-6 bg-cronus-surface">
          <div className="flex items-center text-cronus-gray mb-4 font-mono text-xs uppercase tracking-widest">
            <PlayCircle className="w-4 h-4 mr-2" /> Total Videos
          </div>
          <div className="font-sans font-bold text-5xl text-cronus-white">{STATS.totalVideos}</div>
        </div>
        <div className="border-2 border-cronus-gray/30 p-6 bg-cronus-surface">
          <div className="flex items-center text-cronus-gray mb-4 font-mono text-xs uppercase tracking-widest">
            <Activity className="w-4 h-4 mr-2" /> Total Views
          </div>
          <div className="font-sans font-bold text-5xl text-cronus-white">{STATS.totalViews}</div>
        </div>
        <div className="border-2 border-cronus-red p-6 bg-cronus-red/10 shadow-[4px_4px_0px_0px_rgba(255,34,0,0.3)]">
          <div className="flex items-center text-cronus-red mb-4 font-mono text-xs uppercase tracking-widest">
            <Clock className="w-4 h-4 mr-2" /> Agent Uptime
          </div>
          <div className="font-sans font-bold text-5xl text-cronus-red">{STATS.uptime}</div>
        </div>
      </div>

      {/* Pending Queue */}
      <section>
        <h2 className="font-mono text-xl uppercase mb-6 text-cronus-white border-b-2 border-cronus-gray/30 pb-2 flex items-center">
          Pending Queue <span className="ml-3 text-cronus-gray text-sm">({QUEUE.length})</span>
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {QUEUE.map((item) => (
            <div key={item.id} className="border-2 border-cronus-gray/30 bg-cronus-surface flex flex-col group hover:border-cronus-red transition-colors">
              <div className="h-32 bg-cronus-gray/10 flex items-center justify-center border-b-2 border-cronus-gray/30">
                <span className="font-mono text-xs text-cronus-gray/50 uppercase tracking-widest">Thumbnail Gen</span>
              </div>
              <div className="p-4 flex-1 flex flex-col">
                <div className="flex justify-between items-start mb-2">
                  <span className="font-mono text-[10px] uppercase bg-cronus-gray/20 text-cronus-white px-2 py-1">{item.topic}</span>
                  <span className={`font-mono text-[10px] uppercase font-bold px-2 py-1 ${item.status === "ASSEMBLING" ? "bg-yellow-500/20 text-yellow-500 border border-yellow-500" : "bg-cronus-gray/20 text-cronus-gray"}`}>
                    {item.status}
                  </span>
                </div>
                <h3 className="font-sans font-bold text-lg text-cronus-white leading-tight mb-4">{item.title}</h3>
                <div className="mt-auto font-mono text-xs text-cronus-red flex items-center uppercase font-bold border-t-2 border-cronus-gray/30 pt-3">
                  <Clock className="w-3 h-3 mr-2" /> Scheduled: {item.scheduled}
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Recent History */}
      <section>
        <h2 className="font-mono text-xl uppercase mb-6 text-cronus-white border-b-2 border-cronus-gray/30 pb-2 flex items-center">
          Recent History <span className="ml-3 text-cronus-gray text-sm">(Last 30 Days)</span>
        </h2>
        <div className="w-full overflow-x-auto border-2 border-cronus-gray/30 bg-cronus-surface">
          <table className="w-full text-left font-mono text-sm">
            <thead className="bg-cronus-bg text-cronus-gray uppercase text-xs">
              <tr>
                <th className="p-4 border-b-2 border-cronus-gray/30">Run ID</th>
                <th className="p-4 border-b-2 border-cronus-gray/30">Title</th>
                <th className="p-4 border-b-2 border-cronus-gray/30">Characters</th>
                <th className="p-4 border-b-2 border-cronus-gray/30">Status</th>
                <th className="p-4 border-b-2 border-cronus-gray/30 text-right">Date</th>
              </tr>
            </thead>
            <tbody>
              {HISTORY.map((row) => (
                <tr key={row.id} className="border-b-2 border-cronus-gray/10 hover:bg-cronus-bg transition-colors text-cronus-white">
                  <td className="p-4 text-cronus-gray">{row.id}</td>
                  <td className="p-4 font-sans font-bold">{row.title}</td>
                  <td className="p-4 text-xs">{row.characters}</td>
                  <td className="p-4">
                    {row.status === "UPLOADED" ? (
                      <span className="text-green-500 bg-green-500/10 px-2 py-1 border border-green-500 font-bold uppercase text-[10px]">SUCCESS</span>
                    ) : (
                      <span className="text-cronus-red bg-cronus-red/10 px-2 py-1 border border-cronus-red font-bold uppercase text-[10px] flex items-center w-fit">
                        <AlertTriangle className="w-3 h-3 mr-1" /> {row.status}
                      </span>
                    )}
                  </td>
                  <td className="p-4 text-right text-cronus-gray text-xs">{row.date}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
