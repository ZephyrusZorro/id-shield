import { Loader2, Printer, CheckCircle2, XCircle, AlertTriangle, Info } from "lucide-react";
import { useApi } from "../../hooks/useApi";
import type { CaseReportResponse, KeyFinding } from "../../types/api";

function FindingIcon({ level }: { level: KeyFinding["level"] }) {
  switch (level) {
    case "error":
      return <XCircle size={16} className="mt-0.5 shrink-0 text-rose-500" aria-hidden="true" />;
    case "warning":
      return <AlertTriangle size={16} className="mt-0.5 shrink-0 text-amber-500" aria-hidden="true" />;
    case "success":
      return <CheckCircle2 size={16} className="mt-0.5 shrink-0 text-emerald-500" aria-hidden="true" />;
    default:
      return <Info size={16} className="mt-0.5 shrink-0 text-slate-400 dark:text-slate-500" aria-hidden="true" />;
  }
}

const OUTCOME_TONE: Record<string, string> = {
  mismatch: "bg-rose-50 text-rose-700 ring-rose-600/20 dark:bg-rose-950/60 dark:text-rose-300 dark:ring-rose-500/40",
  suspicious: "bg-rose-50 text-rose-700 ring-rose-600/20 dark:bg-rose-950/60 dark:text-rose-300 dark:ring-rose-500/40",
  issues: "bg-rose-50 text-rose-700 ring-rose-600/20 dark:bg-rose-950/60 dark:text-rose-300 dark:ring-rose-500/40",
  matched: "bg-emerald-50 text-emerald-700 ring-emerald-600/20 dark:bg-emerald-950/60 dark:text-emerald-300 dark:ring-emerald-500/40",
  single_source: "bg-blue-50 text-blue-700 ring-blue-600/20 dark:bg-blue-950/60 dark:text-blue-300 dark:ring-blue-500/40",
  reuse_detected: "bg-amber-50 text-amber-700 ring-amber-600/25 dark:bg-amber-950/60 dark:text-amber-300 dark:ring-amber-500/40",
  warnings: "bg-amber-50 text-amber-700 ring-amber-600/25 dark:bg-amber-950/60 dark:text-amber-300 dark:ring-amber-500/40",
  partial: "bg-amber-50 text-amber-700 ring-amber-600/25 dark:bg-amber-950/60 dark:text-amber-300 dark:ring-amber-500/40",
  unavailable: "bg-slate-100 text-slate-600 ring-slate-500/20 dark:bg-slate-800 dark:text-slate-300 dark:ring-slate-700",
  not_applicable: "bg-slate-100 text-slate-600 ring-slate-500/20 dark:bg-slate-800 dark:text-slate-300 dark:ring-slate-700",
};

function outcomeTone(outcome: string): string {
  return (
    OUTCOME_TONE[outcome] ?? "bg-emerald-50 text-emerald-700 ring-emerald-600/20 dark:bg-emerald-950/60 dark:text-emerald-300"
  );
}

export function ReportTab({ caseId }: { caseId: string }) {
  const { data, loading, error } = useApi<CaseReportResponse>(
    `/api/cases/${caseId}/report`,
  );

  if (loading)
    return (
      <div className="flex items-center justify-center gap-3 py-16 text-xs text-slate-500 dark:text-slate-400 font-medium">
        <Loader2 size={18} className="animate-spin text-blue-500" aria-hidden="true" /> Assembling verification dossier &amp; explainability logs…
      </div>
    );
  if (error)
    return (
      <p role="alert" className="rounded-xl bg-rose-50 dark:bg-rose-950/60 p-4 text-xs font-semibold text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800">
        {error}
      </p>
    );
  if (!data) return null;

  const recTone =
    data.recommendation === "verification_passed"
      ? "bg-emerald-600 dark:bg-emerald-500"
      : data.recommendation === "review_recommended"
        ? "bg-amber-500"
        : data.recommendation === "manual_review_required"
          ? "bg-rose-600 dark:bg-rose-500"
          : "bg-slate-500";
  const recText = (data.recommendation ?? "unable_to_verify").replace(/_/g, " ").toUpperCase();

  return (
    <div className="report-root space-y-6 animate-fade-in">
      {/* Header */}
      <div className="card flex flex-wrap items-start justify-between gap-4 p-6 border border-slate-200/90 dark:border-slate-800">
        <div>
          <p className="text-base font-extrabold text-slate-900 dark:text-white">ID-SHIELD Forensic Audit Dossier</p>
          <p className="mt-0.5 text-xs text-slate-600 dark:text-slate-300 font-medium">
            Case #{data.case_number} — {data.case_name}
          </p>
          <p className="text-[11px] text-slate-400 dark:text-slate-500">
            Generated {new Date(data.generated_at).toLocaleString()}
          </p>
        </div>
        <button type="button" onClick={() => window.print()} className="btn-secondary no-print text-xs shadow-sm flex items-center gap-1.5">
          <Printer size={14} aria-hidden="true" />
          <span>Print / Save PDF Dossier</span>
        </button>
      </div>

      {/* Risk verdict banner */}
      <div className="card flex flex-wrap items-center gap-x-10 gap-y-4 p-6 border border-slate-200/90 dark:border-slate-800">
        <div>
          <p className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">Composite Risk Score</p>
          <div className="mt-1 flex items-end gap-2">
            <span
              className={`text-5xl font-black font-mono leading-none ${
                (data.overall_risk ?? 0) >= 60
                  ? "text-rose-600 dark:text-rose-400"
                  : (data.overall_risk ?? 0) >= 30
                    ? "text-amber-600 dark:text-amber-400"
                    : "text-emerald-600 dark:text-emerald-400"
              }`}
            >
              {data.overall_risk ?? "—"}
            </span>
            <span className="pb-1 text-sm font-bold text-slate-400 dark:text-slate-500">/ 100</span>
          </div>
          {data.band && (
            <p className="mt-1 text-xs font-extrabold uppercase tracking-widest text-slate-900 dark:text-white">
              {data.band} RISK
            </p>
          )}
        </div>
        <div>
          <p className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Automated Audit Recommendation
          </p>
          <span
            className={`mt-2 inline-flex rounded-xl px-4 py-2 text-xs font-extrabold uppercase tracking-wide text-white shadow-sm ${recTone}`}
          >
            Human Verification Required — {recText}
          </span>
        </div>
      </div>

      {/* Screening summary */}
      <section className="card p-6 print-section border border-slate-200/90 dark:border-slate-800">
        <h4 className="mb-3 text-xs font-bold uppercase tracking-wider text-slate-900 dark:text-white">Screening Pipeline Summary</h4>
        <ul className="divide-y divide-slate-100 dark:divide-slate-800/80 text-xs">
          {data.screening_summary.map((m) => (
            <li key={m.module} className="flex flex-wrap items-center justify-between gap-2 py-3">
              <span className="font-bold text-slate-900 dark:text-white sm:w-48">{m.module}</span>
              <span className="flex-1 px-2 text-slate-600 dark:text-slate-300 font-medium">{m.detail}</span>
              <span
                className={`rounded-full px-2.5 py-0.5 text-[11px] font-bold uppercase tracking-wide ring-1 ring-inset ${outcomeTone(m.outcome)}`}
              >
                {m.outcome.replace(/_/g, " ")}
              </span>
            </li>
          ))}
        </ul>
      </section>

      {/* Key findings */}
      <section className="card p-6 print-section border border-slate-200/90 dark:border-slate-800">
        <h4 className="mb-3 text-xs font-bold uppercase tracking-wider text-slate-900 dark:text-white">Explainable Key Findings</h4>
        {data.key_findings.length === 0 ? (
          <p className="text-xs text-slate-400 dark:text-slate-500">No notable findings recorded.</p>
        ) : (
          <ul className="space-y-2.5">
            {data.key_findings.map((f, i) => (
              <li key={i} className="flex items-start gap-2.5 rounded-lg p-2 hover:bg-slate-50/60 dark:hover:bg-slate-800/40 transition-colors">
                <FindingIcon level={f.level} />
                <span
                  className={`text-xs leading-relaxed font-medium ${
                    f.level === "error"
                      ? "text-rose-700 dark:text-rose-300 font-semibold"
                      : f.level === "warning"
                        ? "text-amber-800 dark:text-amber-300 font-semibold"
                        : f.level === "success"
                          ? "text-emerald-700 dark:text-emerald-300"
                          : "text-slate-700 dark:text-slate-300"
                  }`}
                >
                  {f.text}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* Evidence ledger */}
      {data.factors.length > 0 && (
        <section className="card p-6 print-section border border-slate-200/90 dark:border-slate-800">
          <h4 className="mb-3 text-xs font-bold uppercase tracking-wider text-slate-900 dark:text-white">Risk Score Evidence Ledger</h4>
          <table className="w-full text-xs">
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/80">
              {data.factors.map((f) => (
                <tr key={f.factor}>
                  <td className="w-16 py-2.5 pr-3 text-right">
                    <span
                      className={`font-mono font-bold ${f.direction === "increase" ? "text-rose-600 dark:text-rose-400" : "text-emerald-600 dark:text-emerald-400"}`}
                    >
                      {f.score > 0 ? `+${f.score}` : f.score}
                    </span>
                  </td>
                  <td className="py-2.5 text-slate-700 dark:text-slate-300 font-medium">{f.explanation}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {/* Document details */}
      <section className="card p-6 print-section border border-slate-200/90 dark:border-slate-800">
        <h4 className="mb-4 text-xs font-bold uppercase tracking-wider text-slate-900 dark:text-white">Extracted Document Data</h4>
        <div className="space-y-4">
          {data.documents.map((d) => (
            <div key={d.document_id} className="rounded-xl border border-slate-200/80 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/40 p-4">
              <div className="mb-2 flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 dark:border-slate-800/80 pb-2">
                <p className="text-xs font-bold text-slate-900 dark:text-white">{d.file_name}</p>
                <p className="text-[11px] capitalize text-slate-500 dark:text-slate-400 font-medium">
                  {d.document_type?.replace(/_/g, " ") ?? "unclassified"}
                  {d.ocr_mean_confidence !== null && ` · OCR ${Math.round(d.ocr_mean_confidence)}%`}
                  {" · "}
                  {d.validation_overall?.replace(/_/g, " ") ?? "—"}
                </p>
              </div>
              {d.fields.length > 0 ? (
                <table className="w-full text-xs">
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
                    {d.fields.map((f, i) => (
                      <tr key={`${i}-${f.label}-${f.value}`}>
                        <td className="py-1.5 pr-4 text-[11px] font-bold uppercase tracking-wide text-slate-500 dark:text-slate-400 sm:w-48">
                          {f.label}
                        </td>
                        <td className="py-1.5 font-semibold text-slate-900 dark:text-slate-100">{f.value}</td>
                        <td className="w-16 py-1.5 text-right font-mono text-[11px] text-slate-400 dark:text-slate-500">
                          {f.confidence !== null ? `${Math.round(f.confidence)}%` : ""}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="text-xs text-slate-400 dark:text-slate-500">No fields extracted.</p>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Disclaimer */}
      <p className="rounded-xl bg-slate-100 dark:bg-slate-900/60 p-4 text-[11px] leading-relaxed text-slate-500 dark:text-slate-400 border border-slate-200/60 dark:border-slate-800">
        {data.disclaimer}
      </p>
    </div>
  );
}
