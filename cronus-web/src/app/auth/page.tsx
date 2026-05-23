"use client";

import { useState } from "react";
import { ArrowRight, Terminal } from "lucide-react";

export default function AuthPage() {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Supabase auth will be wired in Phase 2
    console.log("Submit:", { email, password, mode: isLogin ? "login" : "signup" });
  };

  return (
    <div className="min-h-screen bg-cronus-bg flex flex-col items-center justify-center p-6">
      <div className="w-full max-w-md">
        <div className="border-2 border-cronus-gray/30 p-2 mb-6 bg-cronus-surface text-cronus-gray font-mono text-xs uppercase tracking-widest flex items-center justify-center">
          <Terminal className="w-4 h-4 mr-2" />
          Terminal Access Required
        </div>

        <div className="border-2 border-cronus-white bg-cronus-surface p-8 shadow-[8px_8px_0px_0px_rgba(255,34,0,0.3)]">
          <h1 className="font-sans font-bold text-4xl uppercase mb-8 text-cronus-white">
            {isLogin ? "Authenticate" : "Initialize"}
            <span className="text-cronus-red">_</span>
          </h1>

          <div className="flex mb-8 border-b-2 border-cronus-gray/30">
            <button
              onClick={() => setIsLogin(true)}
              className={`flex-1 pb-3 font-mono text-sm uppercase tracking-wider font-bold transition-colors ${
                isLogin
                  ? "text-cronus-red border-b-2 border-cronus-red -mb-[2px]"
                  : "text-cronus-gray hover:text-cronus-white"
              }`}
            >
              Login
            </button>
            <button
              onClick={() => setIsLogin(false)}
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
                onChange={(e) => setEmail(e.target.value)}
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
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-cronus-bg border-2 border-cronus-gray/30 text-cronus-white px-4 py-3 font-mono text-sm focus:outline-none focus:border-cronus-red transition-colors"
                placeholder="••••••••••••"
                required
              />
            </div>

            <button
              type="submit"
              className="w-full flex items-center justify-center font-sans font-bold text-xl uppercase px-8 py-4 bg-cronus-red text-cronus-white border-2 border-cronus-red hover:bg-cronus-bg hover:text-cronus-red transition-colors mt-8"
            >
              {isLogin ? "Access System" : "Create Profile"}
              <ArrowRight className="ml-2 w-5 h-5" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
