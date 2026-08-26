import { Loader2, Printer, CheckCircle2, XCircle, AlertTriangle, Info } from "lucide-react";
import { useApi } from "../../hooks/useApi";
import type { CaseReportResponse, KeyFinding } from "../../types/api";

function FindingIcon({ level }: { level: KeyFinding["level"] }) {
  switch (level) {
    case "error":
      return <XCircle size={16} className="mt-0.5 shrink-0 text-red-500" aria-hidden="true" />;
    case "warning":
      return <AlertTriangle size={16} className="mt-0.5 shrink-0 text-amber-500" aria-hidden="true" />;
    case "success":
      return <CheckCircle2 size={16} className="mt-0.5 shrink-0 text-emerald-500" aria-hidden="true" />;
    default:
      return <Info size={16} className="mt-0.5 shrink-0 text-slate-400" aria-hidden="true" />;
  }
}

const OUTCOME_TONE: Record<string, string> = {
  mismatch: "bg-red-50 text-red-700 ring-red-600/20",
  suspicious: "bg-red-50 text-red-700 ring-red-600/20",
  issues: "bg-red-50 text-red-700 ring-red-600/20",
  reuse_detected: "bg-amber-50 text-amber-700 ring-amber-600/25",
  warnings: "bg-amber-50 text-amber-700 ring-amber-600/25",
  partial: "bg-amber-50 text-amber-700 ring-amber-600/25",
  unavailable: "bg-slate-100 text-slate-600 ring-slate-500/20",
  not_applicable: "bg-slate-100 text-slate-600 ring-slate-500/20",
};

function outcomeTone(outcome: string): string {
  return (
    OUTCOME_TONE[outcome] ?? "bg-emerald-50 text-emerald-700 ring-emerald-600/20"
  );
}

export function ReportTab({ caseId }: { caseId: string }) {
  const { data, loading, error } = useApi<CaseReportResponse>(
    `/api/cases/${caseId}/report`,
  );

  if (loading)
    return (
      <div className="flex items-center justify-center gap-3 py-16 text-sm text-slate-500">
        <Loader2 size={18} className="animate-spin" aria-hidden="true" /> Assembling report…
      </div>
    );
  if (error)
    return (
      <p role="alert" className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
        {error}
      </p>
    );
  if (!data) return null;

  const recTone =
    data.recommendation === "verification_passed"
      ? "bg-emerald-600"
      : data.recommendation === "review_recommended"
        ? "bg-amber-500"
        : data.recommendation === "manual_review_required"
          ? "bg-red-600"
          : "bg-slate-500";
  const recText = (data.recommendation ?? "unable_to_verify").replace(/_/g, " ").toUpperCase();

  return (
    <div className="report-root space-y-5">
      {/* Header */}
      <div className="card flex flex-wrap items-start justify-between gap-4 p-6">
        <div>
          <p className="text-lg font-bold text-navy-900">ID-SHIELD Verification Report</p>
          <p className="mt-0.5 text-sm text-slate-500">
            Case #{data.case_number} — {data.case_name}
          </p>
          <p className="text-xs text-slate-400">
            Generated {new Date(data.generated_at).toLocaleString()}
          </p>
        </div>
        <button type="button" onClick={() => window.print()} className="btn-secondary no-print">
          <Printer size={15} aria-hidden="true" /> Print / Save PDF
        </button>
      </div>

      {/* Risk verdict banner */}
      <div className={`card flex flex-wrap items-center gap-x-10 gap-y-4 p-6`}>
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Overall risk</p>
          <div className="mt-1 flex items-end gap-2">
            <span
              className={`text-5xl font-bold leading-none ${
                (data.overall_risk ?? 0) >= 60
                  ? "text-red-600"
                  : (data.overall_risk ?? 0) >= 30
                    ? "text-amber-600"
                    : "text-emerald-600"
              }`}
            >
              {data.overall_risk ?? "—"}
            </span>
            <span className="pb-1 text-sm font-semibold text-slate-400">/ 100</span>
          </div>
          {data.band && (
            <p className="mt-1 text-xs font-bold uppercase tracking-widest text-navy-900">
              {data.band} RISK
            </p>
          )}
        </div>
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
            Recommendation
          </p>
          <span
            className={`mt-2 inline-flex rounded-lg px-4 py-2 text-sm font-bold uppercase tracking-wide text-white ${recTone}`}
          >
            Human verification required — {recText}
          </span>
        </div>
      </div>

      {/* Screening summary */}
      <section className="card p-6 print-section">
        <h4 className="mb-3 text-sm font-bold text-navy-900">Screening Summary</h4>
        <ul className="divide-y divide-slate-100">
          {data.screening_summary.map((m) => (
            <li key={m.module} className="flex flex-wrap items-center justify-between gap-2 py-2.5">
              <span className="text-sm font-medium text-navy-900">{m.module}</span>
              <span className="flex-1 px-4 text-xs text-slate-500">{m.detail}</span>
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
      <section className="card p-6 print-section">
        <h4 className="mb-3 text-sm font-bold text-navy-900">Key Findings</h4>
        {data.key_findings.length === 0 ? (
          <p className="text-sm text-slate-400">No notable findings recorded.</p>
        ) : (
          <ul className="space-y-2">
            {data.key_findings.map((f, i) => (
              <li key={i} className="flex items-start gap-2.5">
                <FindingIcon level={f.level} />
                <span
                  className={`text-sm leading-relaxed ${
                    f.level === "error"
                      ? "font-medium text-red-700"
                      : f.level === "warning"
                        ? "text-amber-800"
                        : f.level === "success"
                          ? "text-emerald-700"
                          : "text-slate-600"
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
        <section className="card p-6 print-section">
          <h4 className="mb-3 text-sm font-bold text-navy-900">Risk Score Evidence Ledger</h4>
          <table className="w-full">
            <tbody className="divide-y divide-slate-100">
              {data.factors.map((f) => (
                <tr key={f.factor}>
                  <td className="w-16 py-2 pr-2 text-right">
                    <span
                      className={`font-bold ${f.direction === "increase" ? "text-red-600" : "text-emerald-600"}`}
                    >
                      {f.score > 0 ? `+${f.score}` : f.score}
                    </span>
                  </td>
                  <td className="py-2 text-sm text-slate-700">{f.explanation}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {/* Document details */}
      <section className="card p-6 print-section">
        <h4 className="mb-4 text-sm font-bold text-navy-900">Document Details</h4>
        <div className="space-y-5">
          {data.documents.map((d) => (
            <div key={d.document_id} className="rounded-lg border border-slate-200 p-4">
              <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                <p className="text-sm font-semibold text-navy-900">{d.file_name}</p>
                <p className="text-xs capitalize text-slate-500">
                  {d.document_type?.replace(/_/g, " ") ?? "unclassified"}
                  {d.ocr_mean_confidence !== null && ` · OCR ${Math.round(d.ocr_mean_confidence)}%`}
                  {" · "}
                  {d.validation_overall?.replace(/_/g, " ") ?? "—"}
                </p>
              </div>
              {d.fields.length > 0 ? (
                <table className="w-full text-sm">
                  <tbody className="divide-y divide-slate-100">
                    {d.fields.map((f, i) => (
                      <tr key={`${i}-${f.label}-${f.value}`}>
                        <td className="py-1.5 pr-4 text-xs font-semibold uppercase tracking-wide text-slate-500">
                          {f.label}
                        </td>
                        <td className="py-1.5 font-medium text-navy-900">{f.value}</td>
                        <td className="w-16 py-1.5 text-right text-xs text-slate-400">
                          {f.confidence !== null ? `${Math.round(f.confidence)}%` : ""}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="text-xs text-slate-400">No fields extracted.</p>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Disclaimer */}
      <p className="rounded-lg bg-slate-100 px-4 py-3 text-[11px] leading-relaxed text-slate-500">
        {data.disclaimer}
      </p>
    </div>
  );
}
