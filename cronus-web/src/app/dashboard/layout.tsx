import { Sidebar } from "@/components/layout/sidebar";
import { Navbar } from "@/components/layout/navbar";
import { createClient } from "@/lib/supabase/server";
import { redirect } from "next/navigation";

export const dynamic = 'force-dynamic';

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

  if (!user) {
    redirect("/auth");
  }

  // Guard: Plan Selection
  const { data: plan } = await supabase.from('plans').select('id').eq('user_id', user.id).single();
  if (!plan) { redirect("/onboard/plan"); }

  // Guard: YouTube Connection
  const { data: yt } = await supabase.from('youtube_connections').select('id').eq('user_id', user.id).single();
  if (!yt) { redirect("/onboard/youtube"); }

  // Guard: Niche & Schedule Config
  const { data: config } = await supabase.from('user_configs').select('niche').eq('user_id', user.id).single();
  if (!config?.niche) { redirect("/onboard/niche"); }

  return (
    <div className="flex min-h-screen bg-cronus-bg">
      <Sidebar />
      <div className="flex-1 flex flex-col min-h-screen overflow-hidden">
        <Navbar />
        <main className="flex-1 overflow-y-auto p-8">
          {children}
        </main>
      </div>
    </div>
  );
}
