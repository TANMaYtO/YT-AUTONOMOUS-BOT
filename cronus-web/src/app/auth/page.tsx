"use client";

import { useState } from "react";
import { ArrowRight, Terminal } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { useRouter } from "next/navigation";

export default function AuthPage() {
  const router = useRouter();
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [confirmEmail, setConfirmEmail] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setErrorMessage(null);
    const supabase = createClient();

    if (isLogin) {
      const { error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (error) {
        setErrorMessage(error.message);
        setLoading(false);
      } else {
        const { data: { user } } = await supabase.auth.getUser();
        if (user) {
          const { data: plan } = await supabase.from('plans').select('id').eq('user_id', user.id).single();
          if (!plan) { router.push("/onboard/plan"); return; }
          const { data: yt } = await supabase.from('youtube_connections').select('id').eq('user_id', user.id).single();
          if (!yt) { router.push("/onboard/youtube"); return; }
          const { data: config } = await supabase.from('user_configs').select('niche').eq('user_id', user.id).single();
          if (!config?.niche) { router.push("/onboard/niche"); return; }
        }
        router.push("/dashboard");
      }
    } else {
      const { error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          emailRedirectTo: `${window.location.origin}/auth`,
        },
      });

      if (error) {
        setErrorMessage(error.message);
        setLoading(false);
      } else {
        setConfirmEmail(true);
        setLoading(false);
      }
    }
  };

  const handleTabSwitch = (loginMode: boolean) => {
    setIsLogin(loginMode);
    setErrorMessage(null);
  };

  const handleInputChange = (setter: React.Dispatch<React.SetStateAction<string>>) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setter(e.target.value);
    setErrorMessage(null);
  };

  return (
    <div className="min-h-screen bg-cronus-bg flex flex-col items-center justify-center p-6">
      <div className="w-full max-w-md">
        <div className="border-2 border-cronus-gray/30 p-2 mb-6 bg-cronus-surface text-cronus-gray font-mono text-xs uppercase tracking-widest flex items-center justify-center">
          <Terminal className="w-4 h-4 mr-2" />
          Terminal Access Required
        </div>

        <div className="border-2 border-cronus-white bg-cronus-surface p-8 shadow-[8px_8px_0px_0px_rgba(255,34,0,0.3)]">
          {confirmEmail ? (
            <div className="text-center">
              <div className="font-mono text-xl uppercase text-cronus-white mb-4">
                CHECK YOUR EMAIL
                <span className="text-cronus-red">_</span>
              </div>
              <p className="font-mono text-sm text-cronus-gray">
                Confirmation link sent to {email}
              </p>
              <p className="font-mono text-xs text-cronus-gray mt-2">
                Click the link then return here to login.
              </p>
              <button 
                onClick={() => { setConfirmEmail(false); setIsLogin(true); }}
                className="mt-6 font-mono text-sm text-cronus-red uppercase hover:text-cronus-white transition-colors"
              >
                BACK TO LOGIN →
              </button>
            </div>
          ) : (
            <>
              <h1 className="font-sans font-bold text-4xl uppercase mb-8 text-cronus-white">
                {isLogin ? "Authenticate" : "Initialize"}
                <span className="text-cronus-red">_</span>
              </h1>

              <div className="flex mb-8 border-b-2 border-cronus-gray/30">
                <button
                  onClick={() => handleTabSwitch(true)}
                  className={`flex-1 pb-3 font-mono text-sm uppercase tracking-wider font-bold transition-colors ${
                    isLogin
                      ? "text-cronus-red border-b-2 border-cronus-red -mb-[2px]"
                      : "text-cronus-gray hover:text-cronus-white"
                  }`}
                >
                  Login
                </button>
                <button
                  onClick={() => handleTabSwitch(false)}
                  className={`flex-1 pb-3 font-mono text-sm uppercase tracking-wider font-bold transition-colors ${
                    !isLogin
                      ? "text-cronus-red border-b-2 border-cronus-red -mb-[2px]"
                      : "text-cronus-gray hover:text-cronus-white"
                  }`}
                >
                  Sign Up
                </button>
              </div>

              <form onSubmit={handleSubmit} className="space-y-6">
                <div>
                  <label className="block font-mono text-xs uppercase tracking-widest text-cronus-gray mb-2">
                    Email Address
                  </label>
                  <input
                    type="email"
                    value={email}
                    onChange={handleInputChange(setEmail)}
                    className="w-full bg-cronus-bg border-2 border-cronus-gray/30 text-cronus-white px-4 py-3 font-mono text-sm focus:outline-none focus:border-cronus-red transition-colors"
                    placeholder="OPERATOR@CRONUS.SYS"
                    required
                  />
                </div>
                <div>
                  <label className="block font-mono text-xs uppercase tracking-widest text-cronus-gray mb-2">
                    Access Code (Password)
                  </label>
                  <input
                    type="password"
                    value={password}
                    onChange={handleInputChange(setPassword)}
                    className="w-full bg-cronus-bg border-2 border-cronus-gray/30 text-cronus-white px-4 py-3 font-mono text-sm focus:outline-none focus:border-cronus-red transition-colors"
                    placeholder="••••••••••••"
                    required
                  />
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full flex items-center justify-center font-sans font-bold text-xl uppercase px-8 py-4 bg-cronus-red text-cronus-white border-2 border-cronus-red hover:bg-cronus-bg hover:text-cronus-red transition-colors mt-8 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loading ? "PROCESSING..." : isLogin ? "Access System" : "Create Profile"}
                  {!loading && <ArrowRight className="ml-2 w-5 h-5" />}
                </button>

                {errorMessage && (
                  <div className="mt-4 p-3 border-2 border-cronus-red bg-cronus-red/10 font-mono text-xs text-cronus-red uppercase">
                    {errorMessage}
                  </div>
                )}
              </form>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
