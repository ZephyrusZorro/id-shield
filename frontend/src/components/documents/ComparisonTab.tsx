import { AlertTriangle, CheckCircle2, Loader2, MinusCircle } from "lucide-react";
import { useApi } from "../../hooks/useApi";
import type { CaseComparisonResponse, ComparisonFieldRow } from "../../types/api";

function FieldBlock({ row }: { row: ComparisonFieldRow }) {
  const mismatch = row.status === "mismatch";
  const single = row.status === "single_source";

  return (
    <section className="card overflow-hidden">
      <div
        className={`flex flex-wrap items-center justify-between gap-2 border-b px-5 py-3.5 ${
          mismatch ? "border-red-100 bg-red-50/50" : "border-slate-100 bg-slate-50/60"
        }`}
      >
        <div className="flex items-center gap-2.5">
          {mismatch ? (
            <AlertTriangle size={18} className="text-red-500" aria-hidden="true" />
          ) : single ? (
            <MinusCircle size={18} className="text-slate-400" aria-hidden="true" />
          ) : (
            <CheckCircle2 size={18} className="text-emerald-500" aria-hidden="true" />
          )}
          <h4 className="text-sm font-bold text-navy-900">{row.label}</h4>
          {mismatch && (
            <span className="rounded-full bg-red-600 px-2.5 py-0.5 text-[11px] font-bold uppercase tracking-wide text-white">
              Mismatch
            </span>
          )}
        </div>
        {!single && !mismatch && (
          <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-emerald-600">
            <CheckCircle2 size={14} aria-hidden="true" /> Consistent across documents
          </span>
        )}
        {single && <span className="text-xs text-slate-400">Present in one document only</span>}
      </div>

      <table className="w-full">
        <tbody className="divide-y divide-slate-100">
          {row.values.map((v) => (
            <tr
              key={`${row.field_name}-${v.document_id}`}
              className={v.agrees ? "" : "bg-red-50/60"}
            >
              <td className="px-5 py-3 text-xs font-medium text-slate-500 sm:w-56">
                <div className="flex items-center">
                  {row.field_name === "facial_photo" && v.document_id && (
                    <img
                      src={`/api/documents/${v.document_id}/face-crop`}
                      alt={v.file_name}
                      className="mr-2 h-6 w-6 rounded object-cover ring-1 ring-slate-200"
                    />
                  )}
                  <span>{v.file_name}</span>
                  {!v.agrees && (
                    <span className="ml-2 rounded bg-red-100 px-1.5 py-0.5 text-[10px] font-bold uppercase text-red-700">
                      differs
                    </span>
                  )}
                </div>
              </td>
              <td className="px-5 py-3">
                <span
                  className={`text-sm ${
                    v.agrees ? "font-medium text-navy-900" : "font-bold text-red-700"
                  }`}
                >
                  {v.normalized_value ?? v.raw_value}
                </span>
              </td>
              <td className="hidden px-5 py-3 text-right text-xs text-slate-400 md:table-cell">
                {v.confidence !== null ? `${Math.round(v.confidence)}% conf.` : ""}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {mismatch && row.explanation && (
        <p className="border-t border-red-100 bg-red-50/40 px-5 py-3 text-xs leading-relaxed text-red-700">
          {row.explanation}
        </p>
      )}
    </section>
  );
}

export function ComparisonTab({ caseId }: { caseId: string }) {
  const { data, loading, error } = useApi<CaseComparisonResponse>(
    `/api/cases/${caseId}/comparison`,
  );

  if (loading)
    return (
      <div className="flex items-center justify-center gap-3 py-16 text-sm text-slate-500">
        <Loader2 size={18} className="animate-spin" aria-hidden="true" /> Building comparison…
      </div>
    );
  if (error)
    return (
      <p role="alert" className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
        {error}
      </p>
    );
  if (!data || data.fields.length === 0)
    return (
      <p className="py-10 text-center text-sm text-slate-400">
        No extracted fields available to compare yet.
      </p>
    );

  const mismatches = data.fields.filter((f) => f.status === "mismatch").length;
  const consistent = data.fields.filter((f) => f.status === "consistent").length;

  return (
    <div className="space-y-4">
      {/* Summary */}
      <div className="card flex flex-wrap items-center gap-x-6 gap-y-2 p-4">
        <p className="text-sm font-bold text-navy-900">Document Comparison</p>
        <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-emerald-600">
          <CheckCircle2 size={14} aria-hidden="true" /> {consistent} consistent
        </span>
        <span
          className={`inline-flex items-center gap-1.5 text-xs font-semibold ${
            mismatches > 0 ? "text-red-600" : "text-slate-400"
          }`}
        >
          <AlertTriangle size={14} aria-hidden="true" /> {mismatches} mismatch
          {mismatches === 1 ? "" : "es"}
        </span>
        <span className="ml-auto text-[11px] text-slate-400">
          Values are OCR-derived evidence for human review.
        </span>
      </div>

      {data.fields.map((row) => (
        <FieldBlock key={row.field_name} row={row} />
      ))}
    </div>
  );
}
