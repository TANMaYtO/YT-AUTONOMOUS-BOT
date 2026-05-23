import Link from "next/link";
import { ArrowRight, Play, Terminal } from "lucide-react";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-cronus-bg flex flex-col items-center">
      <nav className="w-full max-w-7xl mx-auto flex items-center justify-between p-6 border-b-2 border-cronus-gray/30">
        <h1 className="font-sans font-bold text-3xl tracking-tighter uppercase text-cronus-white">
          Cronus<span className="text-cronus-red">_</span>
        </h1>
        <Link
          href="/auth"
          className="font-mono text-sm uppercase px-6 py-3 border-2 border-cronus-white hover:bg-cronus-white hover:text-cronus-bg transition-colors font-bold"
        >
          Initialize // Login
        </Link>
      </nav>

      <main className="flex-1 w-full max-w-7xl mx-auto flex flex-col items-center justify-center p-6 mt-20">
        <div className="border-2 border-cronus-red p-2 mb-8 bg-cronus-red/10 text-cronus-red font-mono text-xs uppercase tracking-widest flex items-center">
          <Terminal className="w-4 h-4 mr-2" />
          System Active: Autonomous Agent Online
        </div>

        <h2 className="font-sans font-bold text-7xl md:text-9xl tracking-tighter uppercase text-center text-cronus-white leading-none mb-6">
          Zero Human
          <br />
          <span className="text-cronus-red">Input.</span>
        </h2>

        <p className="font-mono text-cronus-gray max-w-2xl text-center text-lg md:text-xl mb-12">
          The ultimate hyper-brutalist autonomous engine for YouTube Shorts. Configure once. Let the agent ideate, generate, render, and upload forever.
        </p>

        <div className="flex flex-col sm:flex-row gap-6">
          <Link
            href="/auth"
            className="flex items-center justify-center font-sans font-bold text-xl uppercase px-12 py-6 bg-cronus-red text-cronus-white border-2 border-cronus-red hover:bg-cronus-bg hover:text-cronus-red transition-all shadow-[8px_8px_0px_0px_rgba(255,34,0,0.3)] hover:shadow-none hover:translate-x-2 hover:translate-y-2"
          >
            Deploy Agent <ArrowRight className="ml-3 w-6 h-6" />
          </Link>
          <a
            href="#demo"
            className="flex items-center justify-center font-sans font-bold text-xl uppercase px-12 py-6 bg-cronus-surface text-cronus-white border-2 border-cronus-gray hover:border-cronus-white transition-all shadow-[8px_8px_0px_0px_rgba(136,136,136,0.3)] hover:shadow-none hover:translate-x-2 hover:translate-y-2"
          >
            <Play className="mr-3 w-6 h-6" /> Watch Demo
          </a>
        </div>
      </main>

      <footer className="w-full max-w-7xl mx-auto mt-32 border-t-2 border-cronus-gray/30 p-6 flex flex-col md:flex-row items-center justify-between font-mono text-sm text-cronus-gray uppercase">
        <p>© 2026 CRONUS AGENTIC SYSTEMS. ALL RIGHTS RESERVED.</p>
        <div className="flex gap-6 mt-4 md:mt-0">
          <a href="#" className="hover:text-cronus-white transition-colors">Documentation</a>
          <a href="#" className="hover:text-cronus-white transition-colors">Status</a>
          <a href="#" className="hover:text-cronus-white transition-colors">GitHub</a>
        </div>
      </footer>
    </div>
  );
}
