import {
  AlertTriangle,
  CheckCircle2,
  Loader2,
  MinusCircle,
  ShieldCheck,
  ShieldAlert,
  Calendar,
  UserCheck,
  Hash,
} from "lucide-react";
import { useApi } from "../../hooks/useApi";
import type {
  CaseComparisonResponse,
  ComparisonFieldRow,
  RuleEvaluationItem,
} from "../../types/api";

function RuleCard({ rule }: { rule: RuleEvaluationItem }) {
  const isPass = rule.status === "pass";
  const isFail = rule.status === "fail";
  const isWarn = rule.status === "warning";


  const getRuleIcon = () => {
    if (rule.rule_id.includes("AGE")) return <Calendar size={16} />;
    if (rule.rule_id.includes("PAN")) return <Hash size={16} />;
    if (rule.rule_id.includes("FATHER")) return <UserCheck size={16} />;
    return isPass ? <ShieldCheck size={16} /> : <ShieldAlert size={16} />;
  };

  const badgeTone = isPass
    ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300 ring-emerald-500/30"
    : isFail
      ? "bg-rose-50 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300 ring-rose-500/30"
      : isWarn
        ? "bg-amber-50 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300 ring-amber-500/30"
        : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400 ring-slate-500/20";

  return (
    <div
      className={`rounded-xl border p-4 transition-all ${
        isFail
          ? "border-rose-300 dark:border-rose-900 bg-rose-50/40 dark:bg-rose-950/20"
          : isWarn
            ? "border-amber-300 dark:border-amber-900 bg-amber-50/40 dark:bg-amber-950/20"
            : "border-slate-200/90 dark:border-slate-800 bg-white dark:bg-slate-900/50"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 text-slate-800 dark:text-slate-200 font-bold text-xs">
          <span
            className={`p-1.5 rounded-lg ${
              isPass
                ? "text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/60"
                : isFail
                  ? "text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/60"
                  : "text-slate-500 dark:text-slate-400 bg-slate-100 dark:bg-slate-800"
            }`}
          >
            {getRuleIcon()}
          </span>
          <span>{rule.rule_name}</span>
        </div>
        <span
          className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-extrabold uppercase tracking-wide ring-1 ring-inset ${badgeTone}`}
        >
          {rule.status.replace("_", " ")}
        </span>
      </div>
      <p className="mt-2 text-xs leading-relaxed text-slate-600 dark:text-slate-300 font-medium">
        {rule.explanation}
      </p>
    </div>
  );
}

function FieldBlock({ row }: { row: ComparisonFieldRow }) {
  const mismatch = row.status === "mismatch";
  const single = row.status === "single_source";

  return (
    <section className="card overflow-hidden border border-slate-200/90 dark:border-slate-800">
      <div
        className={`flex flex-wrap items-center justify-between gap-2 border-b px-5 py-3.5 ${
          mismatch
            ? "border-rose-200 dark:border-rose-900/50 bg-rose-50/80 dark:bg-rose-950/40"
            : "border-slate-100 dark:border-slate-800 bg-slate-50/80 dark:bg-slate-900/60"
        }`}
      >
        <div className="flex items-center gap-2.5">
          {mismatch ? (
            <AlertTriangle
              size={18}
              className="text-rose-500 dark:text-rose-400 shrink-0"
              aria-hidden="true"
            />
          ) : single ? (
            <MinusCircle
              size={18}
              className="text-slate-400 dark:text-slate-500 shrink-0"
              aria-hidden="true"
            />
          ) : (
            <CheckCircle2
              size={18}
              className="text-emerald-500 dark:text-emerald-400 shrink-0"
              aria-hidden="true"
            />
          )}
          <h4 className="text-sm font-bold text-slate-900 dark:text-white">
            {row.label}
          </h4>
          {mismatch && (
            <span className="rounded-full bg-rose-600 px-2.5 py-0.5 text-[11px] font-extrabold uppercase tracking-wide text-white shadow-sm">
              Mismatch Detected
            </span>
          )}
          {row.similarity !== undefined && row.similarity !== null && (
            <span
              className={`rounded-md px-2 py-0.5 text-[11px] font-mono font-bold ${
                row.similarity >= 0.9
                  ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300"
                  : row.similarity >= 0.7
                    ? "bg-amber-50 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300"
                    : "bg-rose-50 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300"
              }`}
            >
              Similarity: {(row.similarity * 100).toFixed(0)}%
            </span>
          )}
        </div>
        {!single && !mismatch && (
          <span className="inline-flex items-center gap-1.5 text-xs font-bold text-emerald-600 dark:text-emerald-400">
            <CheckCircle2 size={14} aria-hidden="true" /> Consistent across all documents
          </span>
        )}
        {single && (
          <span className="text-xs text-slate-500 dark:text-slate-400">
            Present in one document only
          </span>
        )}
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800/80">
            {row.values.map((v) => (
              <tr
                key={`${row.field_name}-${v.document_id}`}
                className={
                  v.agrees
                    ? "hover:bg-slate-50/60 dark:hover:bg-slate-800/40"
                    : "bg-rose-50/60 dark:bg-rose-950/30"
                }
              >
                <td className="px-5 py-3 font-semibold text-slate-700 dark:text-slate-300 sm:w-64">
                  <div className="flex items-center">
                    {row.field_name === "facial_photo" && v.document_id && (
                      <img
                        src={`/api/documents/${v.document_id}/face-crop`}
                        alt={v.file_name}
                        className="mr-2 h-7 w-7 rounded-lg object-cover ring-1 ring-slate-300 dark:ring-slate-700"
                      />
                    )}
                    <span className="truncate">{v.file_name}</span>
                    {!v.agrees && (
                      <span className="ml-2 shrink-0 rounded bg-rose-100 dark:bg-rose-900/60 px-1.5 py-0.5 text-[10px] font-bold uppercase text-rose-700 dark:text-rose-300">
                        conflicts
                      </span>
                    )}
                  </div>
                </td>
                <td className="px-5 py-3">
                  <span
                    className={`text-sm ${
                      v.agrees
                        ? "font-semibold text-slate-900 dark:text-slate-100"
                        : "font-bold text-rose-700 dark:text-rose-300"
                    }`}
                  >
                    {v.normalized_value ?? v.raw_value}
                  </span>
                </td>
                <td className="hidden px-5 py-3 text-right text-xs font-mono text-slate-400 dark:text-slate-500 md:table-cell">
                  {v.confidence !== null ? `${Math.round(v.confidence)}% conf.` : ""}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {mismatch && row.explanation && (
        <div className="border-t border-rose-200 dark:border-rose-900/50 bg-rose-50/60 dark:bg-rose-950/40 px-5 py-3 text-xs leading-relaxed text-rose-800 dark:text-rose-200 font-medium">
          <strong>Explainable finding:</strong> {row.explanation}
        </div>
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
      <div className="flex items-center justify-center gap-3 py-16 text-xs font-medium text-slate-500 dark:text-slate-400">
        <Loader2 size={18} className="animate-spin text-blue-500" aria-hidden="true" />{" "}
        Evaluating cross-document verification rules &amp; evidence…
      </div>
    );
  if (error)
    return (
      <p
        role="alert"
        className="rounded-xl bg-rose-50 dark:bg-rose-950/60 p-4 text-xs font-semibold text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800"
      >
        {error}
      </p>
    );
  if (!data || (data.fields.length === 0 && (!data.rules_evaluated || data.rules_evaluated.length === 0)))
    return (
      <p className="py-12 text-center text-xs text-slate-400 dark:text-slate-500">
        No extracted fields or documents available to compare yet.
      </p>
    );

  const mismatches = data.fields.filter((f) => f.status === "mismatch").length;
  const consistent = data.fields.filter((f) => f.status === "consistent").length;
  const ruleViolations = (data.rules_evaluated || []).filter((r) => r.status === "fail").length;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Summary strip */}
      <div className="card flex flex-wrap items-center gap-x-6 gap-y-2 p-4">
        <p className="text-xs font-bold uppercase tracking-wider text-slate-900 dark:text-white">
          Cross-Document Evidence Fusion
        </p>
        <span className="inline-flex items-center gap-1.5 text-xs font-bold text-emerald-600 dark:text-emerald-400">
          <CheckCircle2 size={15} aria-hidden="true" /> {consistent} Consistent Fields
        </span>
        <span
          className={`inline-flex items-center gap-1.5 text-xs font-bold ${
            mismatches > 0 ? "text-rose-600 dark:text-rose-400" : "text-slate-400 dark:text-slate-500"
          }`}
        >
          <AlertTriangle size={15} aria-hidden="true" /> {mismatches} Field Discrepanc{mismatches === 1 ? "y" : "ies"}
        </span>
        {ruleViolations > 0 && (
          <span className="inline-flex items-center gap-1.5 text-xs font-bold text-rose-600 dark:text-rose-400">
            <ShieldAlert size={15} /> {ruleViolations} Rule Violation{ruleViolations === 1 ? "" : "s"}
          </span>
        )}
        <span className="ml-auto text-[11px] text-slate-400 dark:text-slate-500 font-medium">
          Multi-source agreement strengthens verification confidence.
        </span>
      </div>

      {/* Verification Rule Engine Results */}
      {data.rules_evaluated && data.rules_evaluated.length > 0 && (
        <section className="space-y-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Custom Verification Rules &amp; Chronological Integrity
          </h3>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            {data.rules_evaluated.map((r) => (
              <RuleCard key={r.rule_id} rule={r} />
            ))}
          </div>
        </section>
      )}

      {/* Cross-Document Field Ledger */}
      <section className="space-y-3">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
          Multi-Document Field Comparison Matrix
        </h3>
        <div className="space-y-4">
          {data.fields.map((row) => (
            <FieldBlock key={row.field_name} row={row} />
          ))}
        </div>
      </section>
    </div>
  );
}

