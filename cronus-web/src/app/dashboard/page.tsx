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
  const totalUploaded = allVideos.filter((v) => v.status === "uploaded").length;

  // Fetch agent status from user_configs
  const { data: userConfig } = await supabase
    .from("user_configs")
    .select("is_active")
    .eq("user_id", user.id)
    .single();

  const agentStatus = userConfig?.is_active ? "ACTIVE" : "IDLE";

  // Fetch YouTube connection for token expiry warning
  const { data: ytConnection } = await supabase
    .from("youtube_connections")
    .select("token_expiry")
    .eq("user_id", user.id)
    .single();

  let tokenWarning = null;
  if (ytConnection?.token_expiry) {
    const expiryDate = new Date(ytConnection.token_expiry);
    const now = new Date();
    const timeDiffHours = (expiryDate.getTime() - now.getTime()) / (1000 * 60 * 60);

    if (timeDiffHours <= 0) {
      tokenWarning = "EXPIRED";
    } else if (timeDiffHours <= 24) {
      tokenWarning = "EXPIRING_SOON";
    }
  }

  return (
    <div className="space-y-8">
      {/* Token Expiry Banner */}
      {tokenWarning && (
        <div className={`border-2 p-4 flex items-center justify-between font-mono text-sm uppercase ${tokenWarning === "EXPIRED" ? "border-cronus-red bg-cronus-red/10 text-cronus-red shadow-[4px_4px_0px_0px_rgba(255,34,0,0.3)]" : "border-yellow-500 bg-yellow-500/10 text-yellow-500 shadow-[4px_4px_0px_0px_rgba(234,179,8,0.3)]"}`}>
          <div className="flex items-center">
            <AlertTriangle className="w-5 h-5 mr-3" />
            <span>
              {tokenWarning === "EXPIRED" 
                ? "Your YouTube connection has expired (Google Testing limit). The agent cannot upload." 
                : "Your YouTube connection expires in less than 24 hours (Google Testing limit)."}
            </span>
          </div>
          <a href="/onboard/youtube" className={`px-4 py-2 border-2 uppercase font-bold transition-transform hover:-translate-y-1 hover:translate-x-1 ${tokenWarning === "EXPIRED" ? "border-cronus-red hover:shadow-[-4px_4px_0px_0px_rgba(255,34,0,1)] text-cronus-red" : "border-yellow-500 hover:shadow-[-4px_4px_0px_0px_rgba(234,179,8,1)] text-yellow-500"}`}>
            Reconnect
          </a>
        </div>
      )}

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
            <Activity className="w-4 h-4 mr-2" /> Uploaded
          </div>
          <div className="font-sans font-bold text-5xl text-cronus-white">{totalUploaded}</div>
        </div>
        <div className="border-2 border-cronus-red p-6 bg-cronus-red/10 shadow-[4px_4px_0px_0px_rgba(255,34,0,0.3)]">
          <div className="flex items-center text-cronus-red mb-4 font-mono text-xs uppercase tracking-widest">
            <Clock className="w-4 h-4 mr-2" /> Agent Status
          </div>
          <div className="font-sans font-bold text-5xl text-cronus-red">{agentStatus}</div>
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
