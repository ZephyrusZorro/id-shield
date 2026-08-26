import { useState } from "react";
import { Loader2, ShieldAlert, ShieldCheck, Info } from "lucide-react";
import { useApi } from "../../hooks/useApi";
import { DocImage } from "./DocImage";
import type {
  CaseForensicsResponse,
  DocumentForensicsReport,
  ForensicItem,
} from "../../types/api";

const SUSPICION_TONE: Record<
  DocumentForensicsReport["overall_suspicion"],
  string
> = {
  low: "bg-emerald-50 text-emerald-700 ring-emerald-600/20",
  medium: "bg-amber-50 text-amber-700 ring-amber-600/25",
  high: "bg-red-50 text-red-700 ring-red-600/20",
};

function severityColor(severity: ForensicItem["severity"]): string {
  if (severity === "high") return "border-red-500 bg-red-500/15";
  if (severity === "medium") return "border-amber-500 bg-amber-400/15";
  return "border-slate-400 bg-slate-400/10";
}

/** Preview with percentage-based bbox overlays (scales with the image). */
function AnnotatedPreview({ report }: { report: DocumentForensicsReport }) {
  const [dims, setDims] = useState<{ w: number; h: number } | null>(null);

  return (
    <div className="relative inline-block">
      <DocImage
        src={`/api/documents/${report.document_id}/file`}
        alt={`Document ${report.file_name}`}
        className="max-h-[420px] w-auto rounded-lg border border-slate-200"
        onLoad={(e) => {
          const t = e.currentTarget;
          setDims({ w: t.naturalWidth, h: t.naturalHeight });
        }}
      />
      {dims &&
        report.findings.map((f, i) => {
          const [x, y, w, h] = f.bbox;
          const isStructural = f.severity === "low";
          return (
            <div
              key={i}
              className={`absolute rounded border-2 ${severityColor(f.severity)} ${
                isStructural ? "opacity-40" : "opacity-80"
              }`}
              style={{
                left: `${(x / dims.w) * 100}%`,
                top: `${(y / dims.h) * 100}%`,
                width: `${(w / dims.w) * 100}%`,
                height: `${(h / dims.h) * 100}%`,
              }}
              title={`${f.region} — score ${Math.round(f.score * 100)}`}
            >
              <span
                className={`absolute -top-2 left-1 h-1.5 w-1.5 -translate-y-1/2 rounded-full ${
                  f.severity === "high"
                    ? "bg-red-500"
                    : f.severity === "medium"
                      ? "bg-amber-500"
                      : "bg-slate-400"
                }`}
              />
            </div>
          );
        })}
    </div>
  );
}

function DocumentCard({ report }: { report: DocumentForensicsReport }) {
  return (
    <section className="card p-5">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h4 className="text-sm font-bold text-navy-900">{report.file_name}</h4>
          <p className="text-xs capitalize text-slate-500">
            {report.document_type?.replace(/_/g, " ") ?? "unclassified"} ·{" "}
            {report.findings.length} finding{report.findings.length === 1 ? "" : "s"}
          </p>
        </div>
        <span
          className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-bold uppercase tracking-wide ring-1 ring-inset ${SUSPICION_TONE[report.overall_suspicion]}`}
        >
          {report.overall_suspicion === "low" ? (
            <ShieldCheck size={13} aria-hidden="true" />
          ) : (
            <ShieldAlert size={13} aria-hidden="true" />
          )}
          {report.overall_suspicion} · {report.suspicion_score}/100
        </span>
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[auto_1fr]">
        <AnnotatedPreview report={report} />

        <div>
          {report.findings.length === 0 ? (
            <div className="flex items-start gap-2.5 rounded-lg bg-emerald-50 px-4 py-3">
              <ShieldCheck size={16} className="mt-0.5 shrink-0 text-emerald-600" aria-hidden="true" />
              <p className="text-xs leading-relaxed text-emerald-800">
                No significant tampering indicators detected in this document.
              </p>
            </div>
          ) : (
            <ul className="space-y-3">
              {report.findings.map((f, i) => (
                <li
                  key={i}
                  className={`rounded-lg border-l-4 bg-slate-50/70 p-3 ${
                    f.severity === "high"
                      ? "border-red-500"
                      : f.severity === "medium"
                        ? "border-amber-500"
                        : "border-slate-300"
                  }`}
                >
                  <p className="text-sm font-semibold capitalize text-navy-900">
                    {f.region}{" "}
                    <span className="ml-1 font-mono text-xs font-normal text-slate-400">
                      ({f.bbox.join(", ")})
                    </span>
                  </p>
                  <p className="mt-0.5 text-xs leading-relaxed text-slate-600">
                    {f.explanation}
                  </p>
                  <p className="mt-1 text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                    {f.finding_type.replace(/_/g, " ")} · suspicion score{" "}
                    {Math.round(f.score * 100)}/100
                  </p>
                </li>
              ))}
            </ul>
          )}

          <div className="mt-4 flex items-start gap-2 rounded-lg bg-blue-50/70 px-3 py-2.5">
            <Info size={14} className="mt-0.5 shrink-0 text-blue-500" aria-hidden="true" />
            <p className="text-[11px] leading-relaxed text-blue-800">
              Highlighted regions are indicators of potential manipulation,
              not proof of forgery. Final determination requires human review.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

export function ForensicsTab({ caseId }: { caseId: string }) {
  const { data, loading, error } = useApi<CaseForensicsResponse>(
    `/api/cases/${caseId}/forensics`,
  );

  if (loading)
    return (
      <div className="flex items-center justify-center gap-3 py-16 text-sm text-slate-500">
        <Loader2 size={18} className="animate-spin" aria-hidden="true" /> Analyzing imagery…
      </div>
    );
  if (error)
    return (
      <p role="alert" className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
        {error}
      </p>
    );
  if (!data || data.documents.length === 0)
    return (
      <p className="py-10 text-center text-sm text-slate-400">
        No documents available for forensic analysis.
      </p>
    );

  return (
    <div className="space-y-5">
      {data.documents.map((r) => (
        <DocumentCard key={r.document_id} report={r} />
      ))}
      <p className="text-center text-[11px] text-slate-400">{data.disclaimer}</p>
    </div>
  );
}
