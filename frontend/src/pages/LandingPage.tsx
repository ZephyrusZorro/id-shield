import { useNavigate } from "react-router-dom";
import { ShieldCheck, ArrowRight, ScanSearch, GitCompareArrows, FileSearch } from "lucide-react";

export function LandingPage() {
  const navigate = useNavigate();

  return (
    <div className="flex min-h-screen flex-col bg-navy-950 text-white">
      <div className="flex flex-1 flex-col items-center justify-center px-6 py-16 text-center">
        {/* Logo mark */}
        <div className="animate-rise-in">
          <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-2xl bg-blue-600 shadow-[0_0_60px_rgba(37,99,235,0.35)]">
            <ShieldCheck size={44} aria-hidden="true" />
          </div>
        </div>

        <h1 className="animate-rise-in mt-8 text-4xl font-bold tracking-tight [animation-delay:100ms] sm:text-5xl">
          ID-SHIELD
        </h1>
        <p className="animate-rise-in mt-3 text-lg font-medium text-blue-300 [animation-delay:180ms]">
          Explainable Identity &amp; Document Forensics
        </p>
        <p className="animate-rise-in mx-auto mt-6 max-w-xl text-sm leading-relaxed text-navy-200 [animation-delay:260ms]">
          Analyze identity documents, detect suspicious evidence, compare
          submitted information, and generate an explainable verification
          report. One document can look legitimate — an identity evidence set
          may still be inconsistent.
        </p>

        {/* Workflow chips */}
        <div className="animate-rise-in mt-10 flex flex-wrap items-center justify-center gap-x-6 gap-y-3 [animation-delay:340ms]">
          {[
            { icon: ScanSearch, label: "Extract & Inspect" },
            { icon: GitCompareArrows, label: "Compare & Connect" },
            { icon: FileSearch, label: "Score & Explain" },
          ].map(({ icon: Icon, label }) => (
            <div key={label} className="flex items-center gap-2 text-navy-200">
              <Icon size={16} className="text-blue-400" aria-hidden="true" />
              <span className="text-xs font-semibold uppercase tracking-wider">
                {label}
              </span>
            </div>
          ))}
        </div>

        <button
          type="button"
          onClick={() => navigate("/dashboard")}
          className="btn-primary animate-rise-in mt-12 px-8 py-3 text-base [animation-delay:420ms]"
        >
          Get Started
          <ArrowRight size={18} aria-hidden="true" />
        </button>
      </div>

      <footer className="border-t border-navy-800 px-6 py-4">
        <p className="text-center text-[11px] text-navy-300">
          Smart India Hackathon 2026 · SIH26188 · Team HackHive — Prototype for
          assisted verification. Final decisions remain with authorized human
          personnel.
        </p>
      </footer>
    </div>
  );
}
