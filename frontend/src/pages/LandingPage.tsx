import { useNavigate } from "react-router-dom";
import { ShieldCheck, ArrowRight, ScanSearch, GitCompareArrows, FileSearch, Sparkles, Layers } from "lucide-react";

export function LandingPage() {
  const navigate = useNavigate();

  return (
    <div className="relative flex min-h-screen flex-col overflow-hidden bg-[#070B14] text-white selection:bg-blue-500 selection:text-white">
      {/* High-tech background glow orbs */}
      <div className="pointer-events-none absolute -top-40 left-1/2 -translate-x-1/2 h-[500px] w-[700px] rounded-full bg-gradient-to-tr from-blue-600/20 via-indigo-600/20 to-purple-600/10 blur-[120px]" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-[400px] w-[500px] rounded-full bg-blue-600/10 blur-[100px]" />

      <div className="relative z-10 flex flex-1 flex-col items-center justify-center px-6 py-20 text-center">
        {/* Badge */}
        <div className="animate-rise-in mb-6 inline-flex items-center gap-2 rounded-full border border-blue-500/30 bg-blue-500/10 px-3.5 py-1 text-xs font-semibold text-blue-400 backdrop-blur-md">
          <Sparkles size={14} className="text-blue-400 animate-pulse" />
          <span>Next-Gen Multi-Modal Forensic Screening · SIH 2026</span>
        </div>

        {/* Logo mark */}
        <div className="animate-rise-in mb-8">
          <div className="mx-auto flex h-24 w-24 items-center justify-center rounded-3xl bg-gradient-to-tr from-blue-600 via-indigo-600 to-blue-400 shadow-[0_0_60px_rgba(59,130,246,0.4)]">
            <ShieldCheck size={52} className="text-white" aria-hidden="true" />
          </div>
        </div>

        <h1 className="animate-rise-in text-5xl sm:text-6xl font-black tracking-tight [animation-delay:100ms] text-transparent bg-clip-text bg-gradient-to-b from-white via-slate-100 to-slate-400">
          ID-SHIELD
        </h1>
        <p className="animate-rise-in mt-3 text-lg sm:text-xl font-bold text-blue-400 [animation-delay:180ms] tracking-wide">
          Explainable Identity &amp; Document Forensics Intelligence
        </p>
        <p className="animate-rise-in mx-auto mt-6 max-w-2xl text-sm sm:text-base leading-relaxed text-slate-300 [animation-delay:260ms]">
          Comprehensive 11-stage automated screening evaluating ICAO MRZ checksums, Error Level Analysis (ELA), visual tampering heatmaps, facial biometrics, and cross-document discrepancy detection.
        </p>

        {/* Workflow chips */}
        <div className="animate-rise-in mt-10 flex flex-wrap items-center justify-center gap-4 [animation-delay:340ms]">
          {[
            { icon: ScanSearch, label: "Extract & Deskew" },
            { icon: Layers, label: "Forensic Heatmaps" },
            { icon: GitCompareArrows, label: "Cross-Doc Consistency" },
            { icon: FileSearch, label: "Explainable Risk Scoring" },
          ].map(({ icon: Icon, label }) => (
            <div key={label} className="flex items-center gap-2 rounded-xl border border-slate-800/80 bg-slate-900/60 px-3.5 py-2 text-xs font-semibold text-slate-300 backdrop-blur-sm">
              <Icon size={16} className="text-blue-400" aria-hidden="true" />
              <span>{label}</span>
            </div>
          ))}
        </div>

        <button
          type="button"
          onClick={() => navigate("/dashboard")}
          className="btn-primary animate-rise-in mt-12 px-8 py-3.5 text-base font-bold shadow-glow-blue [animation-delay:420ms] flex items-center gap-2"
        >
          <span>Launch Screening Platform</span>
          <ArrowRight size={18} aria-hidden="true" />
        </button>
      </div>

      <footer className="relative z-10 border-t border-slate-800/80 bg-[#070B14]/80 backdrop-blur-md px-6 py-4">
        <p className="text-center text-[11px] text-slate-500">
          Smart India Hackathon 2026 · Team HackHive · Production Prototype for Assisted Identity Verification
        </p>
      </footer>
    </div>
  );
}
