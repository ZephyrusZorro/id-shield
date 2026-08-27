import { CheckCircle2, XCircle, AlertTriangle, MinusCircle, Loader2 } from "lucide-react";
import { useApi } from "../../hooks/useApi";
import type {
  CaseValidationsResponse,
  CheckStatus,
  DocumentValidationReport,
  OverallValidation,
} from "../../types/api";

function CheckIcon({ status }: { status: CheckStatus }) {
  switch (status) {
    case "pass":
      return <CheckCircle2 size={17} className="shrink-0 text-emerald-500" aria-hidden="true" />;
    case "fail":
      return <XCircle size={17} className="shrink-0 text-rose-500" aria-hidden="true" />;
    case "warning":
      return <AlertTriangle size={17} className="shrink-0 text-amber-500" aria-hidden="true" />;
    default:
      return <MinusCircle size={17} className="shrink-0 text-slate-400 dark:text-slate-500" aria-hidden="true" />;
  }
}

const OVERALL_LABEL: Record<OverallValidation, string> = {
  valid: "VALID",
  review_required: "REVIEW REQUIRED",
  unable_to_verify: "UNABLE TO VERIFY",
};

const OVERALL_TONE: Record<OverallValidation, string> = {
  valid: "bg-emerald-50 text-emerald-700 ring-emerald-600/20 dark:bg-emerald-950/60 dark:text-emerald-300 dark:ring-emerald-500/40",
  review_required: "bg-amber-50 text-amber-700 ring-amber-600/25 dark:bg-amber-950/60 dark:text-amber-300 dark:ring-amber-500/40",
  unable_to_verify: "bg-slate-100 text-slate-700 ring-slate-500/20 dark:bg-slate-800 dark:text-slate-300 dark:ring-slate-700",
};

function DocumentCard({ report }: { report: DocumentValidationReport }) {
  return (
    <section className="card p-5 space-y-4 border border-slate-200/90 dark:border-slate-800">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 dark:border-slate-800 pb-3">
        <div>
          <h4 className="text-sm font-bold text-slate-900 dark:text-white">{report.file_name}</h4>
          <p className="text-xs capitalize text-slate-500 dark:text-slate-400 font-medium">
            {report.document_type?.replace(/_/g, " ") ?? "unclassified"}
          </p>
        </div>
        <span
          className={`inline-flex items-center rounded-full px-3 py-0.5 text-xs font-bold tracking-wide ring-1 ring-inset ${OVERALL_TONE[report.overall_status]}`}
        >
          {OVERALL_LABEL[report.overall_status]}
        </span>
      </div>

      {report.items.length === 0 ? (
        <p className="text-xs text-slate-400 dark:text-slate-500">No validation checks recorded.</p>
      ) : (
        <ul className="space-y-2.5">
          {report.items.map((item, i) => (
            <li key={`${i}-${item.check_type}-${item.message}`} className="flex items-start gap-2.5 rounded-lg p-2 hover:bg-slate-50/70 dark:hover:bg-slate-800/40 transition-colors">
              <span className="mt-0.5"><CheckIcon status={item.status} /></span>
              <div className="min-w-0 flex-1">
                <p className="text-xs font-bold text-slate-900 dark:text-white">{item.check_type}</p>
                <p
                  className={`mt-0.5 text-xs leading-relaxed ${
                    item.status === "fail"
                      ? "text-rose-600 dark:text-rose-400 font-semibold"
                      : item.status === "warning"
                        ? "text-amber-700 dark:text-amber-400 font-medium"
                        : "text-slate-600 dark:text-slate-300"
                  }`}
                >
                  {item.message}
                </p>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export function ValidationTab({ caseId }: { caseId: string }) {
  const { data, loading, error } = useApi<CaseValidationsResponse>(
    `/api/cases/${caseId}/validations`,
  );

  if (loading)
    return (
      <div className="flex items-center justify-center gap-3 py-16 text-xs font-medium text-slate-500 dark:text-slate-400">
        <Loader2 size={18} className="animate-spin text-blue-500" aria-hidden="true" /> Verifying structural &amp; checksum rules…
      </div>
    );
  if (error)
    return (
      <p role="alert" className="rounded-xl bg-rose-50 dark:bg-rose-950/60 p-4 text-xs font-semibold text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800">
        {error}
      </p>
    );
  if (!data || data.documents.length === 0)
    return (
      <p className="py-12 text-center text-xs text-slate-400 dark:text-slate-500">
        No documents to validate in this case.
      </p>
    );

  return (
    <div className="grid grid-cols-1 gap-5 xl:grid-cols-2 animate-fade-in">
      {data.documents.map((r) => (
        <DocumentCard key={r.document_id} report={r} />
      ))}
      <p className="col-span-full text-center text-[11px] text-slate-400 dark:text-slate-500 font-medium">
        Validation verifies ICAO MRZ checksums, expiry boundaries, and format patterns deterministically.
      </p>
    </div>
  );
}
