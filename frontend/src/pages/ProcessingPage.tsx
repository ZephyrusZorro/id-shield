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
} from "lucide-react";
import { apiGet } from "../services/api";
import type { AnalysisResponse, StageStatus } from "../types/api";

const POLL_MS = 900;
const MAX_CONSECUTIVE_ERRORS = 8;

function StageIcon({ status }: { status: StageStatus }) {
  switch (status) {
    case "done":
      return <CheckCircle2 size={20} className="shrink-0 text-emerald-500" aria-hidden="true" />;
    case "running":
      return <Loader2 size={20} className="shrink-0 animate-spin text-blue-600" aria-hidden="true" />;
    case "warning":
      return <AlertTriangle size={20} className="shrink-0 text-amber-500" aria-hidden="true" />;
    case "unavailable":
      return <MinusCircle size={20} className="shrink-0 text-slate-400" aria-hidden="true" />;
    case "error":
      return <XCircle size={20} className="shrink-0 text-red-500" aria-hidden="true" />;
    default:
      return <CircleDashed size={20} className="shrink-0 text-slate-300" aria-hidden="true" />;
  }
}

const STATUS_TEXT: Record<StageStatus, string> = {
  pending: "text-slate-400",
  running: "text-navy-900",
  done: "text-navy-900",
  warning: "text-navy-900",
  unavailable: "text-slate-400",
  error: "text-red-600",
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


  return (
    <div className="mx-auto max-w-2xl animate-fade-in">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-navy-900">
            {finished ? "Analysis Complete" : "Analyzing Case"}
          </h2>
          <p className="mt-0.5 text-sm text-slate-500">
            {finished ? "Review the results below" : "This takes a few seconds"}
          </p>
        </div>
      </div>

      <div className="card p-6">
        {error && !gaveUp && (
          <p role="alert" className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </p>
        )}

        {gaveUp && (
          <div role="alert" className="mb-4 rounded-lg bg-red-50 p-4 text-sm text-red-700">
            <p className="font-medium">Lost connection to the backend.</p>
            <p className="mt-1">Stopped polling after several failed attempts.</p>
            <div className="mt-3 flex gap-2">
              <button
                type="button"
                onClick={() => window.location.reload()}
                className="rounded-md bg-red-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-red-700"
              >
                Retry
              </button>
              <Link
                to="/"
                className="rounded-md border border-red-200 px-3 py-1.5 text-xs font-semibold text-red-700 hover:bg-red-100"
              >
                Back to Dashboard
              </Link>
            </div>
          </div>
        )}

        {!analysis && !error && (
          <div className="flex items-center justify-center gap-3 py-10 text-sm text-slate-500">
            <Loader2 size={18} className="animate-spin" aria-hidden="true" />
            Loading pipeline status…
          </div>
        )}

        {analysis && (
          <ol className="space-y-1" aria-live="polite" aria-label="Analysis pipeline progress">
            {analysis.stages.map((stage) => (
              <li key={stage.stage_key} className="rounded-lg px-3 py-3">
                <div className="flex items-center gap-3">
                  <StageIcon status={stage.status} />
                  <span
                    className={`flex-1 text-sm font-medium ${STATUS_TEXT[stage.status]}`}
                  >
                    {stage.stage_label}
                  </span>
                  {stage.duration_ms !== null && stage.status === "done" && (
                    <span className="text-xs text-slate-400">{stage.duration_ms} ms</span>
                  )}
                </div>
                {stage.detail && (
                  <p
                    className={`ml-8 mt-1 text-xs leading-relaxed ${
                      stage.status === "error" ? "text-red-600" : "text-slate-400"
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
          <Link to={`/cases/${caseId}`} className="btn-primary mt-5 w-full">
            View Evidence
            <ArrowRight size={15} aria-hidden="true" />
          </Link>
        )}
      </div>
    </div>
  );
}
