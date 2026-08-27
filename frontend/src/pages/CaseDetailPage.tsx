import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft,
  FileText,
  Loader2,
  AlertTriangle,
  CheckCircle2,
  MessageSquare,
  Send,
} from "lucide-react";
import { PageHeader } from "../components/layout/PageHeader";
import { ValidationTab } from "../components/documents/ValidationTab";
import { ComparisonTab } from "../components/documents/ComparisonTab";
import { ForensicsTab } from "../components/documents/ForensicsTab";
import { FaceVerificationTab } from "../components/documents/FaceVerificationTab";
import { ReportTab } from "../components/documents/ReportTab";
import { NotificationsTab } from "../components/notifications/NotificationsTab";
import { NotificationModal } from "../components/notifications/NotificationModal";
import { DocImage } from "../components/documents/DocImage";
import { useApi } from "../hooks/useApi";
import type { RiskReport, CaseDetail, DocumentDetail } from "../types/api";
import { TrendingDown, TrendingUp, ShieldAlert, ShieldCheck, HelpCircle } from "lucide-react";

function riskTone(score: number): string {
  if (score >= 60) return "text-rose-600 dark:text-rose-400";
  if (score >= 30) return "text-amber-600 dark:text-amber-400";
  return "text-emerald-600 dark:text-emerald-400";
}

function recommendationLabel(rec: string | null): { text: string; tone: string; icon: typeof ShieldCheck } {
  switch (rec) {
    case "verification_passed":
      return { text: "Verification Passed", tone: "bg-emerald-50 text-emerald-700 ring-emerald-600/20 dark:bg-emerald-950/60 dark:text-emerald-300 dark:ring-emerald-500/40", icon: ShieldCheck };
    case "review_recommended":
      return { text: "Review Recommended", tone: "bg-amber-50 text-amber-700 ring-amber-600/25 dark:bg-amber-950/60 dark:text-amber-300 dark:ring-amber-500/40", icon: ShieldAlert };
    case "manual_review_required":
      return { text: "Manual Review Required", tone: "bg-rose-50 text-rose-700 ring-rose-600/20 dark:bg-rose-950/60 dark:text-rose-300 dark:ring-rose-500/40", icon: ShieldAlert };
    default:
      return { text: "Unable to Verify", tone: "bg-slate-100 text-slate-600 ring-slate-500/20 dark:bg-slate-800 dark:text-slate-300 dark:ring-slate-700", icon: HelpCircle };
  }
}

function RiskPanel({ caseId }: { caseId: string }) {
  const { data: risk } = useApi<RiskReport>(`/api/cases/${caseId}/risk`);
  if (!risk || (risk.score === null && risk.factors.length === 0)) return null;

  const rec = recommendationLabel(risk.recommendation);
  const RecIcon = rec.icon;

  return (
    <section className="card mt-6 p-5 border-slate-200/90 dark:border-slate-800" aria-label="Risk assessment">
      <div className="flex flex-wrap items-center gap-8">
        {/* Score */}
        <div className="min-w-[180px]">
          <p className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Overall Risk Score
          </p>
          <div className="mt-1 flex items-end gap-2">
            <span className={`text-5xl font-black leading-none font-mono ${risk.score !== null ? riskTone(risk.score) : "text-slate-400"}`}>
              {risk.score ?? "—"}
            </span>
            <span className="pb-1 text-sm font-bold text-slate-400 dark:text-slate-500">/ 100</span>
          </div>
          {/* Score bar */}
          <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
            <div
              className={`h-full rounded-full transition-all duration-700 ${
                (risk.score ?? 0) >= 60 ? "bg-rose-500 shadow-glow-rose" : (risk.score ?? 0) >= 30 ? "bg-amber-500" : "bg-emerald-500 shadow-glow-emerald"
              }`}
              style={{ width: `${risk.score ?? 0}%` }}
            />
          </div>
          {risk.band && (
            <p className="mt-1.5 text-xs font-extrabold uppercase tracking-wider text-navy-900 dark:text-white">
              {risk.band} RISK BAND
            </p>
          )}
        </div>

        {/* Recommendation */}
        <div>
          <p className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Automated Recommendation
          </p>
          <span
            className={`mt-2 inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-bold ring-1 ring-inset ${rec.tone}`}
          >
            <RecIcon size={14} aria-hidden="true" />
            Decision: {rec.text}
          </span>
        </div>

        {/* Contribution ledger */}
        {risk.factors.length > 0 && (
          <div className="min-w-[260px] flex-1">
            <p className="mb-2 text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              Evidence Factors &amp; Point Adjustments
            </p>
            <ul className="space-y-1.5">
              {risk.factors.map((f) => (
                <li key={f.factor} className="flex items-start gap-2 text-xs">
                  {f.direction === "increase" ? (
                    <TrendingUp size={14} className="mt-0.5 shrink-0 text-rose-500" aria-hidden="true" />
                  ) : (
                    <TrendingDown size={14} className="mt-0.5 shrink-0 text-emerald-500" aria-hidden="true" />
                  )}
                  <span className={`font-mono font-bold ${f.direction === "increase" ? "text-rose-600 dark:text-rose-400" : "text-emerald-600 dark:text-emerald-400"}`}>
                    {f.score > 0 ? `+${f.score}` : f.score}
                  </span>
                  <span className="text-slate-700 dark:text-slate-300 font-medium">{f.explanation}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </section>
  );
}

const TABS = [
  "Overview",
  "Documents",
  "Validation",
  "Forensics",
  "Face Verification",
  "Comparison",
  "Report",
  "Notifications",
] as const;
type Tab = (typeof TABS)[number];

const FIELD_LABELS: Record<string, string> = {
  full_name: "Name",
  document_number: "Document Number",
  date_of_birth: "Date of Birth",
  gender: "Gender",
  nationality: "Nationality",
  issue_date: "Date of Issue",
  expiry_date: "Date of Expiry",
  address: "Address",
};

function formatFieldName(key: string): string {
  return (
    FIELD_LABELS[key] ??
    key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
  );
}

function ConfidenceChip({ value }: { value: number | null }) {
  if (value === null) return <span className="text-xs text-slate-400 dark:text-slate-500">—</span>;
  const tone =
    value >= 85
      ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-400"
      : value >= 65
        ? "bg-amber-50 text-amber-700 dark:bg-amber-950/60 dark:text-amber-400"
        : "bg-rose-50 text-rose-700 dark:bg-rose-950/60 dark:text-rose-400";
  return (
    <span className={`rounded-md px-2 py-0.5 text-xs font-mono font-bold ${tone}`}>
      {value.toFixed(0)}%
    </span>
  );
}

function DocumentsTab({ caseData }: { caseData: CaseDetail }) {
  const [selectedId, setSelectedId] = useState<string | null>(
    caseData.documents[0]?.id ?? null,
  );
  const { data: doc, loading, error } = useApi<DocumentDetail>(
    selectedId ? `/api/documents/${selectedId}` : null,
  );

  return (
    <div className="grid grid-cols-1 gap-5 lg:grid-cols-[280px_1fr]">
      {/* Document list */}
      <ul className="space-y-2" aria-label="Case documents">
        {caseData.documents.map((d) => (
          <li key={d.id}>
            <button
              type="button"
              onClick={() => setSelectedId(d.id)}
              className={`w-full rounded-xl border p-3 text-left transition-all ${
                selectedId === d.id
                  ? "border-blue-500 bg-blue-50/80 dark:bg-blue-950/40 shadow-glow-blue"
                  : "border-slate-200/90 dark:border-slate-800 bg-white dark:bg-slate-900/60 hover:bg-slate-50 dark:hover:bg-slate-800/50"
              }`}
            >
              <p className="truncate text-xs font-bold text-navy-900 dark:text-white">{d.file_name}</p>
              <p className="mt-1 text-[11px] capitalize text-slate-500 dark:text-slate-400 font-medium">
                {d.document_type
                  ? `${d.document_type.replace(/_/g, " ")}${
                      d.type_confidence !== null
                        ? ` · ${Math.round(d.type_confidence * 100)}%`
                        : ""
                    }`
                  : "type pending"}
              </p>
            </button>
          </li>
        ))}
      </ul>

      {/* Detail panel */}
      <div className="card p-5">
        {loading && (
          <div className="flex items-center justify-center gap-3 py-16 text-xs text-slate-500 dark:text-slate-400">
            <Loader2 size={18} className="animate-spin text-blue-500" aria-hidden="true" /> Loading document details…
          </div>
        )}
        {error && (
          <p role="alert" className="rounded-xl bg-rose-50 dark:bg-rose-950/60 p-4 text-xs font-semibold text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800">
            {error}
          </p>
        )}
        {!loading && !error && doc && (
          <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(220px,320px)_1fr]">
            {/* Preview */}
            <div>
              {doc.has_preview ? (
                <DocImage
                  src={`/api/documents/${doc.id}/file`}
                  alt={`Uploaded document ${doc.file_name}`}
                  className="w-full rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm"
                />
              ) : (
                <div className="flex aspect-[3/2] items-center justify-center rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/60">
                  <FileText size={40} className="text-slate-400 dark:text-slate-600" aria-hidden="true" />
                </div>
              )}
              <dl className="mt-4 space-y-2 text-xs text-slate-500 dark:text-slate-400 border-t border-slate-100 dark:border-slate-800/80 pt-3">
                <div className="flex justify-between">
                  <dt>OCR Engine</dt>
                  <dd className="font-semibold text-navy-900 dark:text-slate-200">{doc.ocr_engine ?? "—"}</dd>
                </div>
                <div className="flex justify-between">
                  <dt>OCR Confidence</dt>
                  <dd><ConfidenceChip value={doc.ocr_mean_confidence} /></dd>
                </div>
                <div className="flex justify-between">
                  <dt>SHA-256 Hash</dt>
                  <dd className="font-mono text-[11px] text-navy-900 dark:text-slate-300">{doc.file_hash_prefix ?? "—"}</dd>
                </div>
              </dl>
            </div>

            {/* Extracted fields */}
            <div>
              <h4 className="mb-3 text-xs font-bold uppercase tracking-wider text-navy-900 dark:text-white">
                Structured Field Ledger
              </h4>
              {doc.fields.length === 0 ? (
                <div className="flex items-start gap-2.5 rounded-xl bg-amber-50 dark:bg-amber-950/60 p-4 border border-amber-200 dark:border-amber-800">
                  <AlertTriangle size={16} className="mt-0.5 shrink-0 text-amber-500" aria-hidden="true" />
                  <p className="text-xs leading-relaxed text-amber-800 dark:text-amber-300">
                    No structured fields could be extracted. Check document scan quality.
                  </p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead className="border-b border-slate-100 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-900/60 text-slate-500 dark:text-slate-400">
                      <tr>
                        <th scope="col" className="table-head-cell">Field</th>
                        <th scope="col" className="table-head-cell">Normalized Value</th>
                        <th scope="col" className="table-head-cell">Conf.</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800/80">
                      {doc.fields.map((f, i) => (
                        <tr key={`${i}-${f.field_name}-${f.raw_value}`} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40">
                          <td className="table-cell whitespace-nowrap font-medium text-slate-600 dark:text-slate-400">{formatFieldName(f.field_name)}</td>
                          <td className="table-cell">
                            <span className="font-bold text-navy-900 dark:text-slate-100">{f.normalized_value ?? f.raw_value}</span>
                          </td>
                          <td className="table-cell"><ConfidenceChip value={f.confidence} /></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              <div className="mt-4 flex items-center gap-2 text-[11px] text-slate-400 dark:text-slate-500">
                <CheckCircle2 size={13} aria-hidden="true" className="text-blue-500" />
                Evidence extracted deterministically via multi-pass OCR &amp; MRZ parser.
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export function CaseDetailPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const navigate = useNavigate();
  const [tab, setTab] = useState<Tab>("Overview");
  const [notificationModalOpen, setNotificationModalOpen] = useState(false);
  const {
    data: caseData,
    loading,
    error,
    reload,
  } = useApi<CaseDetail>(caseId ? `/api/cases/${caseId}` : null);

  return (
    <div className="mx-auto max-w-6xl animate-fade-in space-y-6">
      <button
        type="button"
        onClick={() => navigate("/history")}
        className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 dark:text-slate-400 transition-colors hover:text-navy-900 dark:hover:text-white"
      >
        <ArrowLeft size={14} aria-hidden="true" /> Back to screening history
      </button>

      <PageHeader
        title={caseData ? `Case #${caseData.case_number} — ${caseData.case_name}` : "Case Dossier"}
        subtitle="Multi-modal forensic evidence and explainable validation workspace"
        actions={
          caseData && (
            <button
              type="button"
              onClick={() => setNotificationModalOpen(true)}
              className="btn-primary shadow-glow-blue flex items-center gap-2 text-xs"
            >
              <Send size={13} />
              <span>Notify Applicant</span>
            </button>
          )
        }
      />

      <div className="card overflow-hidden">
        {/* Modern Tab Strip */}
        <div role="tablist" aria-label="Case sections" className="flex gap-1 overflow-x-auto border-b border-slate-200/80 dark:border-slate-800 bg-slate-50/80 dark:bg-slate-900/60 px-3 pt-2">
          {TABS.map((t) => (
            <button
              key={t}
              role="tab"
              aria-selected={tab === t}
              type="button"
              onClick={() => setTab(t)}
              className={`whitespace-nowrap rounded-t-lg px-4 py-2.5 text-xs font-bold transition-all ${
                tab === t
                  ? "border-x border-t border-slate-200/90 dark:border-slate-800 bg-white dark:bg-dark-surface text-blue-600 dark:text-blue-400 shadow-sm"
                  : "text-slate-500 dark:text-slate-400 hover:text-navy-900 dark:hover:text-white hover:bg-slate-100/50 dark:hover:bg-slate-800/40"
              }`}
            >
              {t}
            </button>
          ))}
        </div>

        <div className="p-6">
          {loading && (
            <div className="flex items-center justify-center gap-3 py-16 text-xs text-slate-500 dark:text-slate-400">
              <Loader2 size={18} className="animate-spin text-blue-500" aria-hidden="true" /> Loading case dossier…
            </div>
          )}
          {error && (
            <p role="alert" className="rounded-xl bg-rose-50 dark:bg-rose-950/60 p-4 text-xs font-semibold text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800">
              {error}
            </p>
          )}

          {caseData && tab === "Overview" && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                <div className="rounded-xl border border-slate-200/80 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/40 p-4">
                  <p className="text-[11px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">Pipeline Status</p>
                  <p className="mt-1 text-sm font-extrabold capitalize text-navy-900 dark:text-white">{caseData.status}</p>
                </div>
                <div className="rounded-xl border border-slate-200/80 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/40 p-4">
                  <p className="text-[11px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">Evidence Count</p>
                  <p className="mt-1 text-sm font-extrabold text-navy-900 dark:text-white">{caseData.documents.length} Docs</p>
                </div>
                <div className="rounded-xl border border-slate-200/80 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/40 p-4">
                  <p className="text-[11px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">Risk Score</p>
                  {caseData.overall_risk !== null ? (
                    <p className={`mt-1 text-lg font-mono font-black ${riskTone(caseData.overall_risk)}`}>
                      {caseData.overall_risk}/100
                    </p>
                  ) : (
                    <p className="mt-1 text-sm font-bold text-slate-400">Pending</p>
                  )}
                </div>
                <div className="rounded-xl border border-slate-200/80 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/40 p-4">
                  <p className="text-[11px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">Recommendation</p>
                  {caseData.recommendation ? (
                    (() => {
                      const rec = recommendationLabel(caseData.recommendation);
                      return (
                        <span className={`mt-1 inline-flex rounded-full px-2 py-0.5 text-xs font-bold ring-1 ring-inset ${rec.tone}`}>
                          {rec.text}
                        </span>
                      );
                    })()
                  ) : (
                    <p className="mt-1 text-sm font-bold text-slate-400">Evaluating</p>
                  )}
                </div>
              </div>

              {caseId && <RiskPanel caseId={caseId} />}

              {caseData.documents.length > 0 ? (
                <div>
                  <h4 className="mb-3 text-xs font-bold uppercase tracking-wider text-navy-900 dark:text-white">
                    Submitted Evidence Scans
                  </h4>
                  <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
                    {caseData.documents.map((d) => (
                      <figure key={d.id} className="overflow-hidden rounded-xl border border-slate-200/80 dark:border-slate-800 bg-white dark:bg-slate-900/60 shadow-card">
                        {d.has_preview ? (
                          <DocImage
                            src={`/api/documents/${d.id}/file`}
                            alt={`Document ${d.file_name}`}
                            className="aspect-[3/2] w-full object-cover"
                            fallbackClassName="aspect-[3/2] w-full"
                          />
                        ) : (
                          <div className="flex aspect-[3/2] items-center justify-center bg-slate-50 dark:bg-slate-800">
                            <FileText size={32} className="text-slate-400 dark:text-slate-600" aria-hidden="true" />
                          </div>
                        )}
                        <figcaption className="px-3 py-2 border-t border-slate-100 dark:border-slate-800/80">
                          <p className="truncate text-xs font-bold text-navy-900 dark:text-white">{d.file_name}</p>
                          <p className="text-[11px] capitalize text-slate-500 dark:text-slate-400 font-medium">
                            {d.document_type?.replace(/_/g, " ") ?? "unclassified"}
                          </p>
                        </figcaption>
                      </figure>
                    ))}
                  </div>
                  <div className="mt-5 flex flex-wrap items-center gap-3">
                    <button type="button" onClick={() => setTab("Documents")} className="btn-secondary text-xs">
                      Inspect Extracted Fields
                    </button>
                    <button type="button" onClick={() => setTab("Face Verification")} className="btn-secondary text-xs">
                      Inspect Facial Biometrics
                    </button>
                    <button
                      type="button"
                      onClick={() => setNotificationModalOpen(true)}
                      className="btn-secondary text-xs text-blue-600 dark:text-blue-400 border-blue-200 dark:border-blue-800"
                    >
                      <MessageSquare size={13} />
                      <span>Send Discrepancy Notice</span>
                    </button>
                  </div>
                </div>
              ) : (
                <p className="text-xs text-slate-500 dark:text-slate-400">No documents in this case yet.</p>
              )}
            </div>
          )}

          {caseData && tab === "Documents" && <DocumentsTab caseData={caseData} />}

          {caseData && tab === "Validation" && caseId && <ValidationTab caseId={caseId} />}

          {caseData && tab === "Comparison" && caseId && <ComparisonTab caseId={caseId} />}

          {caseData && tab === "Forensics" && caseId && <ForensicsTab caseId={caseId} />}

          {caseData && tab === "Face Verification" && caseId && (
            <FaceVerificationTab caseId={caseId} />
          )}

          {caseData && tab === "Report" && caseId && <ReportTab caseId={caseId} />}

          {caseData && tab === "Notifications" && caseId && (
            <NotificationsTab
              caseId={caseId}
              caseData={caseData}
              onRefreshCase={() => reload()}
            />
          )}
        </div>
      </div>

      {/* Discrepancy Notification Modal */}
      {caseId && (
        <NotificationModal
          caseId={caseId}
          isOpen={notificationModalOpen}
          onClose={() => setNotificationModalOpen(false)}
          onSent={() => reload()}
        />
      )}
    </div>
  );
}
