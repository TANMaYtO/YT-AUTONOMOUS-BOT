import { Activity, PlayCircle, Clock, AlertTriangle } from "lucide-react";
import { createClient } from "@/lib/supabase/server";

export const dynamic = 'force-dynamic';

export default async function DashboardPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

  if (!user) return null;

  // Fetch all videos for the user
  const { data: videos } = await supabase
    .from("videos")
    .select("*")
    .eq("user_id", user.id)
    .order("created_at", { ascending: false });

  const allVideos = videos || [];

  // Derived State
  const queue = allVideos.filter((v) => v.status === "pending");
  const history = allVideos.filter((v) => v.status === "uploaded" || v.status === "failed").slice(0, 50);
  const totalVideos = allVideos.length;
  // Mock views for now since YouTube API sync isn't built
  const totalViews = "0";
  const uptime = "100%";

  return (
    <div className="space-y-8">
      {/* Stats Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="border-2 border-cronus-gray/30 p-6 bg-cronus-surface">
          <div className="flex items-center text-cronus-gray mb-4 font-mono text-xs uppercase tracking-widest">
            <PlayCircle className="w-4 h-4 mr-2" /> Total Videos
          </div>
          <div className="font-sans font-bold text-5xl text-cronus-white">{totalVideos}</div>
        </div>
        <div className="border-2 border-cronus-gray/30 p-6 bg-cronus-surface">
          <div className="flex items-center text-cronus-gray mb-4 font-mono text-xs uppercase tracking-widest">
            <Activity className="w-4 h-4 mr-2" /> Total Views
          </div>
          <div className="font-sans font-bold text-5xl text-cronus-white">{totalViews}</div>
        </div>
        <div className="border-2 border-cronus-red p-6 bg-cronus-red/10 shadow-[4px_4px_0px_0px_rgba(255,34,0,0.3)]">
          <div className="flex items-center text-cronus-red mb-4 font-mono text-xs uppercase tracking-widest">
            <Clock className="w-4 h-4 mr-2" /> Agent Uptime
          </div>
          <div className="font-sans font-bold text-5xl text-cronus-red">{uptime}</div>
        </div>
      </div>

      {/* Pending Queue */}
      <section>
        <h2 className="font-mono text-xl uppercase mb-6 text-cronus-white border-b-2 border-cronus-gray/30 pb-2 flex items-center">
          Pending Queue <span className="ml-3 text-cronus-gray text-sm">({queue.length})</span>
        </h2>
        
        {queue.length === 0 ? (
          <div className="border-2 border-cronus-gray/30 bg-cronus-surface p-12 text-center text-cronus-gray font-mono text-sm uppercase">
            No videos in queue. The agent is idle.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {queue.map((item) => (
              <div key={item.id} className="border-2 border-cronus-gray/30 bg-cronus-surface flex flex-col group hover:border-cronus-red transition-colors">
                <div className="h-32 bg-cronus-gray/10 flex items-center justify-center border-b-2 border-cronus-gray/30">
                  <span className="font-mono text-xs text-cronus-gray/50 uppercase tracking-widest">Generating...</span>
                </div>
                <div className="p-4 flex-1 flex flex-col">
                  <div className="flex justify-between items-start mb-2">
                    <span className="font-mono text-[10px] uppercase bg-cronus-gray/20 text-cronus-white px-2 py-1">{item.topic || "Unknown"}</span>
                    <span className="font-mono text-[10px] uppercase font-bold px-2 py-1 bg-cronus-gray/20 text-cronus-gray">
                      {item.status}
                    </span>
                  </div>
                  <h3 className="font-sans font-bold text-lg text-cronus-white leading-tight mb-4">{item.title || "Untitled Video"}</h3>
                  <div className="mt-auto font-mono text-xs text-cronus-red flex items-center uppercase font-bold border-t-2 border-cronus-gray/30 pt-3">
                    <Clock className="w-3 h-3 mr-2" /> Scheduled: {item.scheduled_upload_time ? new Date(item.scheduled_upload_time).toLocaleString() : "TBD"}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Recent History */}
      <section>
        <h2 className="font-mono text-xl uppercase mb-6 text-cronus-white border-b-2 border-cronus-gray/30 pb-2 flex items-center">
          Recent History <span className="ml-3 text-cronus-gray text-sm">(Last 50 Runs)</span>
        </h2>
        
        {history.length === 0 ? (
          <div className="border-2 border-cronus-gray/30 bg-cronus-surface p-12 text-center text-cronus-gray font-mono text-sm uppercase">
            No history found. Let the agent cook.
          </div>
        ) : (
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
                {history.map((row) => (
                  <tr key={row.id} className="border-b-2 border-cronus-gray/10 hover:bg-cronus-bg transition-colors text-cronus-white">
                    <td className="p-4 text-cronus-gray">{row.run_id || row.id.split("-")[0]}</td>
                    <td className="p-4 font-sans font-bold">{row.title || "Untitled"}</td>
                    <td className="p-4 text-xs">{[row.character_a, row.character_b].filter(Boolean).join(" x ") || "None"}</td>
                    <td className="p-4">
                      {row.status === "uploaded" ? (
                        <span className="text-green-500 bg-green-500/10 px-2 py-1 border border-green-500 font-bold uppercase text-[10px]">SUCCESS</span>
                      ) : (
                        <span className="text-cronus-red bg-cronus-red/10 px-2 py-1 border border-cronus-red font-bold uppercase text-[10px] flex items-center w-fit">
                          <AlertTriangle className="w-3 h-3 mr-1" /> {row.status}
                        </span>
                      )}
                    </td>
                    <td className="p-4 text-right text-cronus-gray text-xs">{new Date(row.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
