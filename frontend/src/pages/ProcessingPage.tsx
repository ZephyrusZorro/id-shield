import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  CheckCircle2,
  Loader2,
  CircleDashed,
  AlertTriangle,
  MinusCircle,
  XCircle,
  ArrowRight,
  Cpu,
} from "lucide-react";
import { apiGet } from "../services/api";
import type { AnalysisResponse, StageStatus } from "../types/api";

const POLL_MS = 800;
const MAX_CONSECUTIVE_ERRORS = 8;

function StageIcon({ status }: { status: StageStatus }) {
  switch (status) {
    case "done":
      return <CheckCircle2 size={19} className="shrink-0 text-emerald-500" aria-hidden="true" />;
    case "running":
      return <Loader2 size={19} className="shrink-0 animate-spin text-blue-500" aria-hidden="true" />;
    case "warning":
      return <AlertTriangle size={19} className="shrink-0 text-amber-500" aria-hidden="true" />;
    case "unavailable":
      return <MinusCircle size={19} className="shrink-0 text-slate-500" aria-hidden="true" />;
    case "error":
      return <XCircle size={19} className="shrink-0 text-rose-500" aria-hidden="true" />;
    default:
      return <CircleDashed size={19} className="shrink-0 text-slate-400 dark:text-slate-600" aria-hidden="true" />;
  }
}

const STATUS_TEXT: Record<StageStatus, string> = {
  pending: "text-slate-400 dark:text-slate-500",
  running: "text-blue-600 dark:text-blue-400 font-semibold",
  done: "text-navy-900 dark:text-slate-100",
  warning: "text-navy-900 dark:text-slate-100",
  unavailable: "text-slate-400 dark:text-slate-500",
  error: "text-rose-600 dark:text-rose-400",
};

export function ProcessingPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [gaveUp, setGaveUp] = useState(false);

  useEffect(() => {
    if (!caseId) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    let consecutiveErrors = 0;

    const poll = async () => {
      try {
        const data = await apiGet<AnalysisResponse>(`/api/cases/${caseId}/analysis`);
        if (cancelled) return;
        setAnalysis(data);
        setError(null);
        consecutiveErrors = 0;
        const busy =
          data.case_status === "processing" ||
          data.case_status === "draft" ||
          data.stages.length === 0 ||
          data.stages.some((s) => s.status === "pending" || s.status === "running");
        if (busy) timer = setTimeout(poll, POLL_MS);
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Failed to load analysis.");
        consecutiveErrors += 1;
        if (consecutiveErrors >= MAX_CONSECUTIVE_ERRORS) {
          if (!cancelled) setGaveUp(true);
          return;
        }
        timer = setTimeout(poll, POLL_MS * 2);
      }
    };
    void poll();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [caseId]);

  const finished =
    analysis !== null &&
    analysis.stages.length > 0 &&
    (analysis.case_status === "completed" || analysis.case_status === "failed") &&
    !analysis.stages.some((s) => s.status === "pending" || s.status === "running");

  const completedCount = analysis?.stages.filter((s) => s.status === "done" || s.status === "warning").length ?? 0;
  const totalCount = analysis?.stages.length || 11;
  const progressPercent = Math.round((completedCount / totalCount) * 100);

  return (
    <div className="mx-auto max-w-2xl animate-fade-in space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="flex h-6 w-6 items-center justify-center rounded-lg bg-blue-100 dark:bg-blue-950/80 text-blue-600 dark:text-blue-400">
              <Cpu size={14} />
            </span>
            <span className="text-xs font-bold uppercase tracking-wider text-blue-600 dark:text-blue-400">
              {finished ? "Screening Complete" : "Pipeline Executing"}
            </span>
          </div>
          <h2 className="mt-1 text-2xl font-extrabold text-navy-900 dark:text-white">
            {finished ? "Multi-Modal Evidence Ready" : "Forensic Pipeline Running"}
          </h2>
          <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
            {finished ? "All forensic models finished evaluating the submitted documents." : "Scanning for visual tampering, OCR fields, MRZ checksums, and face consistency..."}
          </p>
        </div>
        <div className="text-right">
          <span className="text-xl font-black text-navy-900 dark:text-white">{progressPercent}%</span>
          <p className="text-[10px] uppercase tracking-wider text-slate-400">Completed</p>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="h-2 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800">
        <div
          className="h-full bg-gradient-to-r from-blue-600 via-indigo-500 to-emerald-500 transition-all duration-300 shadow-glow-blue"
          style={{ width: `${progressPercent}%` }}
        />
      </div>

      <div className="card p-6 space-y-4">
        {error && !gaveUp && (
          <p role="alert" className="rounded-xl bg-rose-50 dark:bg-rose-950/60 p-4 text-xs font-semibold text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800">
            {error}
          </p>
        )}

        {gaveUp && (
          <div role="alert" className="rounded-xl bg-rose-50 dark:bg-rose-950/60 p-4 text-xs text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800 space-y-2">
            <p className="font-bold">Lost connection to the backend pipeline.</p>
            <p>Polling stopped after repeated retries. Check if the server is still running.</p>
            <div className="pt-2 flex gap-2">
              <button
                type="button"
                onClick={() => window.location.reload()}
                className="rounded-lg bg-rose-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-rose-700 shadow-sm"
              >
                Retry Polling
              </button>
              <Link
                to="/dashboard"
                className="rounded-lg border border-rose-300 dark:border-rose-700 px-3 py-1.5 text-xs font-semibold text-rose-700 dark:text-rose-300 hover:bg-rose-100 dark:hover:bg-rose-900/40"
              >
                Return to Dashboard
              </Link>
            </div>
          </div>
        )}

        {!analysis && !error && (
          <div className="flex items-center justify-center gap-3 py-12 text-xs font-medium text-slate-500 dark:text-slate-400">
            <Loader2 size={18} className="animate-spin text-blue-500" aria-hidden="true" />
            Initializing pipeline stages and loading files…
          </div>
        )}

        {analysis && (
          <ol className="divide-y divide-slate-100 dark:divide-slate-800/80" aria-live="polite" aria-label="Analysis pipeline progress">
            {analysis.stages.map((stage) => (
              <li key={stage.stage_key} className="py-3 first:pt-0 last:pb-0 transition-colors">
                <div className="flex items-center gap-3">
                  <StageIcon status={stage.status} />
                  <span
                    className={`flex-1 text-xs font-semibold ${STATUS_TEXT[stage.status]}`}
                  >
                    {stage.stage_label}
                  </span>
                  {stage.duration_ms !== null && stage.status === "done" && (
                    <span className="text-[11px] font-mono text-slate-400 dark:text-slate-500">{stage.duration_ms} ms</span>
                  )}
                </div>
                {stage.detail && (
                  <p
                    className={`ml-8 mt-1 text-[11px] leading-relaxed ${
                      stage.status === "error" ? "text-rose-600 dark:text-rose-400 font-medium" : "text-slate-500 dark:text-slate-400"
                    }`}
                  >
                    {stage.detail}
                  </p>
                )}
              </li>
            ))}
          </ol>
        )}

        {finished && caseId && (
          <div className="pt-4 border-t border-slate-100 dark:border-slate-800 animate-rise-in">
            <Link to={`/cases/${caseId}`} className="btn-primary w-full shadow-glow-blue flex items-center justify-center gap-2 py-3 text-sm font-bold">
              <span>Inspect Full Evidence &amp; Dossier</span>
              <ArrowRight size={16} aria-hidden="true" />
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
