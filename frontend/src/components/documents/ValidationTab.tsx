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
      return <XCircle size={17} className="shrink-0 text-red-500" aria-hidden="true" />;
    case "warning":
      return <AlertTriangle size={17} className="shrink-0 text-amber-500" aria-hidden="true" />;
    default:
      return <MinusCircle size={17} className="shrink-0 text-slate-400" aria-hidden="true" />;
  }
}

const OVERALL_LABEL: Record<OverallValidation, string> = {
  valid: "VALID",
  review_required: "REVIEW REQUIRED",
  unable_to_verify: "UNABLE TO VERIFY",
};

const OVERALL_TONE: Record<OverallValidation, string> = {
  valid: "bg-emerald-50 text-emerald-700 ring-emerald-600/20",
  review_required: "bg-amber-50 text-amber-700 ring-amber-600/25",
  unable_to_verify: "bg-slate-100 text-slate-600 ring-slate-500/20",
};

function DocumentCard({ report }: { report: DocumentValidationReport }) {
  return (
    <section className="card p-5">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h4 className="text-sm font-bold text-navy-900">{report.file_name}</h4>
          <p className="text-xs capitalize text-slate-500">
            {report.document_type?.replace(/_/g, " ") ?? "unclassified"}
          </p>
        </div>
        <span
          className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-bold tracking-wide ring-1 ring-inset ${OVERALL_TONE[report.overall_status]}`}
        >
          {OVERALL_LABEL[report.overall_status]}
        </span>
      </div>

      {report.items.length === 0 ? (
        <p className="text-sm text-slate-400">No validation checks recorded.</p>
      ) : (
        <ul className="space-y-2">
          {report.items.map((item, i) => (
            <li key={`${i}-${item.check_type}-${item.message}`} className="flex items-start gap-2.5">
              <span className="mt-0.5"><CheckIcon status={item.status} /></span>
              <div className="min-w-0">
                <p className="text-sm font-medium text-navy-900">{item.check_type}</p>
                <p
                  className={`text-xs leading-relaxed ${
                    item.status === "fail"
                      ? "text-red-600"
                      : item.status === "warning"
                        ? "text-amber-700"
                        : "text-slate-500"
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
      <div className="flex items-center justify-center gap-3 py-16 text-sm text-slate-500">
        <Loader2 size={18} className="animate-spin" aria-hidden="true" /> Loading validations…
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
        No documents to validate in this case.
      </p>
    );

  return (
    <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
      {data.documents.map((r) => (
        <DocumentCard key={r.document_id} report={r} />
      ))}
      <p className="col-span-full text-center text-[11px] text-slate-400">
        Validation reflects structural and logical consistency only — it does
        not prove legal authenticity of any document.
      </p>
    </div>
  );
}
