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
import type { RiskReport } from "../types/api";
import { TrendingDown, TrendingUp, ShieldAlert, ShieldCheck, HelpCircle } from "lucide-react";

function riskTone(score: number): string {
  if (score >= 60) return "text-red-600";
  if (score >= 30) return "text-amber-600";
  return "text-emerald-600";
}

function recommendationLabel(rec: string | null): { text: string; tone: string; icon: typeof ShieldCheck } {
  switch (rec) {
    case "verification_passed":
      return { text: "Verification Passed", tone: "bg-emerald-50 text-emerald-700 ring-emerald-600/20", icon: ShieldCheck };
    case "review_recommended":
      return { text: "Review Recommended", tone: "bg-amber-50 text-amber-700 ring-amber-600/25", icon: ShieldAlert };
    case "manual_review_required":
      return { text: "Manual Review Required", tone: "bg-red-50 text-red-700 ring-red-600/20", icon: ShieldAlert };
    default:
      return { text: "Unable to Verify", tone: "bg-slate-100 text-slate-600 ring-slate-500/20", icon: HelpCircle };
  }
}

function RiskPanel({ caseId }: { caseId: string }) {
  const { data: risk } = useApi<RiskReport>(`/api/cases/${caseId}/risk`);
  if (!risk || (risk.score === null && risk.factors.length === 0)) return null;

  const rec = recommendationLabel(risk.recommendation);
  const RecIcon = rec.icon;

  return (
    <section className="card mt-6 p-5" aria-label="Risk assessment">
      <div className="flex flex-wrap items-center gap-8">
        {/* Score */}
        <div className="min-w-[180px]">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
            Overall Risk
          </p>
          <div className="mt-1 flex items-end gap-2">
            <span className={`text-5xl font-bold leading-none ${risk.score !== null ? riskTone(risk.score) : "text-slate-400"}`}>
              {risk.score ?? "—"}
            </span>
            <span className="pb-1 text-sm font-semibold text-slate-400">/ 100</span>
          </div>
          {/* Score bar */}
          <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-slate-100">
            <div
              className={`h-full rounded-full transition-all duration-700 ${
                (risk.score ?? 0) >= 60 ? "bg-red-500" : (risk.score ?? 0) >= 30 ? "bg-amber-500" : "bg-emerald-500"
              }`}
              style={{ width: `${risk.score ?? 0}%` }}
            />
          </div>
          {risk.band && (
            <p className="mt-1.5 text-xs font-bold uppercase tracking-wide text-navy-900">
              {risk.band} RISK
            </p>
          )}
        </div>

        {/* Recommendation */}
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
            Recommendation
          </p>
          <span
            className={`mt-2 inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-bold ring-1 ring-inset ${rec.tone}`}
          >
            <RecIcon size={15} aria-hidden="true" />
            Human verification: {rec.text}
          </span>
        </div>

        {/* Contribution ledger */}
        {risk.factors.length > 0 && (
          <div className="min-w-[260px] flex-1">
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">
              Why this score — contributing evidence
            </p>
            <ul className="space-y-1.5">
              {risk.factors.map((f) => (
                <li key={f.factor} className="flex items-start gap-2 text-xs">
                  {f.direction === "increase" ? (
                    <TrendingUp size={14} className="mt-0.5 shrink-0 text-red-500" aria-hidden="true" />
                  ) : (
                    <TrendingDown size={14} className="mt-0.5 shrink-0 text-emerald-500" aria-hidden="true" />
                  )}
                  <span className={`font-bold ${f.direction === "increase" ? "text-red-600" : "text-emerald-600"}`}>
                    {f.score > 0 ? `+${f.score}` : f.score}
                  </span>
                  <span className="text-slate-600">{f.explanation}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </section>
  );
}
import type { CaseDetail, DocumentDetail } from "../types/api";

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
  if (value === null) return <span className="text-xs text-slate-400">—</span>;
  const tone =
    value >= 85
      ? "bg-emerald-50 text-emerald-700"
      : value >= 65
        ? "bg-amber-50 text-amber-700"
        : "bg-red-50 text-red-700";
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${tone}`}>
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
    <div className="grid grid-cols-1 gap-5 lg:grid-cols-[300px_1fr]">
      {/* Document list */}
      <ul className="space-y-2.5" aria-label="Case documents">
        {caseData.documents.map((d) => (
          <li key={d.id}>
            <button
              type="button"
              onClick={() => setSelectedId(d.id)}
              className={`w-full rounded-lg border p-3 text-left transition-colors ${
                selectedId === d.id
                  ? "border-blue-500 bg-blue-50/60 shadow-card"
                  : "border-slate-200 bg-white hover:bg-slate-50"
              }`}
            >
              <p className="truncate text-sm font-semibold text-navy-900">{d.file_name}</p>
              <p className="mt-1 text-xs capitalize text-slate-500">
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
          <div className="flex items-center justify-center gap-3 py-16 text-sm text-slate-500">
            <Loader2 size={18} className="animate-spin" aria-hidden="true" /> Loading…
          </div>
        )}
        {error && (
          <p role="alert" className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </p>
        )}
        {!loading && !error && doc && (
          <div className="grid grid-cols-1 gap-5 xl:grid-cols-[minmax(220px,320px)_1fr]">
            {/* Preview */}
            <div>
              {doc.has_preview ? (
                <DocImage
                  src={`/api/documents/${doc.id}/file`}
                  alt={`Uploaded document ${doc.file_name}`}
                  className="w-full rounded-lg border border-slate-200"
                />
              ) : (
                <div className="flex aspect-[3/2] items-center justify-center rounded-lg border border-slate-200 bg-slate-50">
                  <FileText size={40} className="text-slate-300" aria-hidden="true" />
                </div>
              )}
              <dl className="mt-4 space-y-1.5 text-xs text-slate-500">
                <div className="flex justify-between">
                  <dt>OCR engine</dt>
                  <dd className="font-semibold text-navy-900">{doc.ocr_engine ?? "—"}</dd>
                </div>
                <div className="flex justify-between">
                  <dt>OCR confidence</dt>
                  <dd><ConfidenceChip value={doc.ocr_mean_confidence} /></dd>
                </div>
                <div className="flex justify-between">
                  <dt>SHA-256</dt>
                  <dd className="font-mono text-[11px] text-navy-900">{doc.file_hash_prefix ?? "—"}</dd>
                </div>
              </dl>
            </div>

            {/* Extracted fields */}
            <div>
              <h4 className="mb-3 text-sm font-bold text-navy-900">Extracted Fields</h4>
              {doc.fields.length === 0 ? (
                <div className="flex items-start gap-2.5 rounded-lg bg-amber-50 px-4 py-3">
                  <AlertTriangle size={16} className="mt-0.5 shrink-0 text-amber-500" aria-hidden="true" />
                  <p className="text-xs leading-relaxed text-amber-800">
                    No structured fields could be extracted. OCR may have been
                    unable to read this document reliably.
                  </p>
                </div>
              ) : (
                <table className="w-full">
                  <thead className="border-b border-slate-100 bg-slate-50/60">
                    <tr>
                      <th scope="col" className="table-head-cell">Field</th>
                      <th scope="col" className="table-head-cell">Extracted Value</th>
                      <th scope="col" className="table-head-cell">Conf.</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {doc.fields.map((f, i) => (
                      <tr key={`${i}-${f.field_name}-${f.raw_value}`}>
                        <td className="table-cell whitespace-nowrap font-medium">{formatFieldName(f.field_name)}</td>
                        <td className="table-cell">
                          <span className="font-semibold text-navy-900">{f.normalized_value ?? f.raw_value}</span>
                        </td>
                        <td className="table-cell"><ConfidenceChip value={f.confidence} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}

              <div className="mt-4 flex items-center gap-2 text-[11px] text-slate-400">
                <CheckCircle2 size={13} aria-hidden="true" />
                Values are OCR-derived evidence — not verified issuer data.
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
    <div className="mx-auto max-w-6xl animate-fade-in">
      <button
        type="button"
        onClick={() => navigate("/history")}
        className="mb-4 inline-flex items-center gap-1.5 text-sm font-semibold text-slate-500 transition-colors hover:text-navy-900"
      >
        <ArrowLeft size={15} aria-hidden="true" /> Back to history
      </button>

      <PageHeader
        title={caseData ? `Case #${caseData.case_number} — ${caseData.case_name}` : "Case"}
        subtitle="Verification evidence workspace"
        actions={
          caseData && (
            <button
              type="button"
              onClick={() => setNotificationModalOpen(true)}
              className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-xs font-bold text-white shadow-sm hover:bg-blue-700 transition-colors"
            >
              <Send size={13} /> Notify Applicant
            </button>
          )
        }
      />

      <div className="card overflow-hidden">
        <div role="tablist" aria-label="Case sections" className="flex gap-1 overflow-x-auto border-b border-slate-200 bg-slate-50/60 px-3 pt-2">
          {TABS.map((t) => (
            <button
              key={t}
              role="tab"
              aria-selected={tab === t}
              type="button"
              onClick={() => setTab(t)}
              className={`whitespace-nowrap rounded-t-lg px-4 py-2.5 text-sm font-semibold transition-colors ${
                tab === t
                  ? "border-x border-t border-slate-200 bg-white text-blue-700"
                  : "text-slate-400 hover:text-navy-900"
              }`}
            >
              {t}
            </button>
          ))}
        </div>

        <div className="p-5">
          {loading && (
            <div className="flex items-center justify-center gap-3 py-16 text-sm text-slate-500">
              <Loader2 size={18} className="animate-spin" aria-hidden="true" /> Loading case…
            </div>
          )}
          {error && (
            <p role="alert" className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </p>
          )}

          {caseData && tab === "Overview" && (
            <div>
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                <div className="rounded-lg border border-slate-200 p-4">
                  <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Status</p>
                  <p className="mt-1 text-sm font-bold capitalize text-navy-900">{caseData.status}</p>
                </div>
                <div className="rounded-lg border border-slate-200 p-4">
                  <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Documents</p>
                  <p className="mt-1 text-sm font-bold text-navy-900">{caseData.documents.length}</p>
                </div>
                <div className="rounded-lg border border-slate-200 p-4">
                  <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Risk Score</p>
                  {caseData.overall_risk !== null ? (
                    <p className={`mt-1 text-lg font-bold ${riskTone(caseData.overall_risk)}`}>
                      {caseData.overall_risk}/100
                    </p>
                  ) : (
                    <p className="mt-1 text-sm font-bold text-slate-400">Not scored yet</p>
                  )}
                </div>
                <div className="rounded-lg border border-slate-200 p-4">
                  <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Recommendation</p>
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
                    <p className="mt-1 text-sm font-bold text-slate-400">Pending analysis</p>
                  )}
                </div>
              </div>

              {caseId && <RiskPanel caseId={caseId} />}

              {caseData.documents.length > 0 ? (
                <>
                  <h4 className="mb-3 mt-6 text-sm font-bold text-navy-900">Submitted Evidence</h4>
                  <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
                    {caseData.documents.map((d) => (
                      <figure key={d.id} className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-card">
                        {d.has_preview ? (
                          <DocImage
                            src={`/api/documents/${d.id}/file`}
                            alt={`Document ${d.file_name}`}
                            className="aspect-[3/2] w-full object-cover"
                            fallbackClassName="aspect-[3/2] w-full"
                          />
                        ) : (
                          <div className="flex aspect-[3/2] items-center justify-center bg-slate-50">
                            <FileText size={32} className="text-slate-300" aria-hidden="true" />
                          </div>
                        )}
                        <figcaption className="px-3 py-2">
                          <p className="truncate text-xs font-semibold text-navy-900">{d.file_name}</p>
                          <p className="text-[11px] capitalize text-slate-500">
                            {d.document_type?.replace(/_/g, " ") ?? "unclassified"}
                          </p>
                        </figcaption>
                      </figure>
                    ))}
                  </div>
                  <div className="mt-5 flex flex-wrap items-center gap-3">
                    <button type="button" onClick={() => setTab("Documents")} className="btn-secondary">
                      Inspect extracted fields
                    </button>
                    <button type="button" onClick={() => setTab("Face Verification")} className="btn-secondary">
                      Inspect facial biometrics
                    </button>
                    <button
                      type="button"
                      onClick={() => setNotificationModalOpen(true)}
                      className="btn-secondary text-blue-700 border-blue-200 hover:bg-blue-50/60"
                    >
                      <MessageSquare size={14} /> Send Discrepancy Notice
                    </button>
                  </div>
                </>
              ) : (
                <p className="mt-6 text-sm text-slate-500">No documents in this case yet.</p>
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

