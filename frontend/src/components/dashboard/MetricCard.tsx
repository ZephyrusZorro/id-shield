import type { LucideIcon } from "lucide-react";

interface MetricCardProps {
  label: string;
  value: string | number;
  icon: LucideIcon;
  tone?: "blue" | "green" | "amber" | "red" | "navy";
  hint?: string;
  loading?: boolean;
}

const TONES: Record<NonNullable<MetricCardProps["tone"]>, string> = {
  blue: "bg-blue-50 text-blue-600 dark:bg-blue-950/60 dark:text-blue-400 dark:border-blue-800/40 border border-blue-100",
  green: "bg-emerald-50 text-emerald-600 dark:bg-emerald-950/60 dark:text-emerald-400 dark:border-emerald-800/40 border border-emerald-100",
  amber: "bg-amber-50 text-amber-600 dark:bg-amber-950/60 dark:text-amber-400 dark:border-amber-800/40 border border-amber-100",
  red: "bg-rose-50 text-rose-600 dark:bg-rose-950/60 dark:text-rose-400 dark:border-rose-800/40 border border-rose-100",
  navy: "bg-slate-100 text-slate-700 dark:bg-slate-800/80 dark:text-slate-300 dark:border-slate-700/60 border border-slate-200",
};

export function MetricCard({
  label,
  value,
  icon: Icon,
  tone = "navy",
  hint,
  loading = false,
}: MetricCardProps) {
  return (
    <div className="card flex items-center gap-4 p-5 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-card-hover dark:hover:border-slate-700">
      <div
        className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-xl shadow-sm ${TONES[tone]}`}
      >
        <Icon size={22} strokeWidth={2} aria-hidden="true" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
          {label}
        </p>
        {loading ? (
          <div
            className="mt-2 h-7 w-20 animate-pulse rounded bg-slate-200 dark:bg-slate-800"
            aria-hidden="true"
          />
        ) : (
          <p className="text-2xl font-extrabold leading-tight text-navy-900 dark:text-white">{value}</p>
        )}
        {hint && !loading && (
          <p className="mt-0.5 truncate text-[11px] text-slate-400 dark:text-slate-500 font-medium">{hint}</p>
        )}
      </div>
    </div>
  );
}

/** Row placeholder for tables while data loads. */
export function SkeletonRows({ rows = 4, cols = 6 }: { rows?: number; cols?: number }) {
  return (
    <tbody aria-hidden="true">
      {Array.from({ length: rows }).map((_, r) => (
        <tr key={r} className="divide-x-0 border-b border-slate-100 dark:border-slate-800/60">
          {Array.from({ length: cols }).map((_, c) => (
            <td key={c} className="px-4 py-4">
              <div
                className="h-3.5 animate-pulse rounded bg-slate-200/70 dark:bg-slate-800"
                style={{ width: `${55 + ((r * 13 + c * 7) % 35)}%` }}
              />
            </td>
          ))}
        </tr>
      ))}
    </tbody>
  );
}
