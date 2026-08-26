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
  blue: "bg-blue-50 text-blue-600",
  green: "bg-emerald-50 text-emerald-600",
  amber: "bg-amber-50 text-amber-600",
  red: "bg-red-50 text-red-600",
  navy: "bg-navy-50 text-navy-600",
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
    <div className="card flex items-center gap-4 p-5 transition-shadow hover:shadow-card-hover">
      <div
        className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-lg ${TONES[tone]}`}
      >
        <Icon size={22} strokeWidth={2} aria-hidden="true" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
          {label}
        </p>
        {loading ? (
          <div
            className="mt-1.5 h-6 w-16 animate-pulse rounded bg-slate-200"
            aria-hidden="true"
          />
        ) : (
          <p className="text-2xl font-bold leading-tight text-navy-900">{value}</p>
        )}
        {hint && !loading && (
          <p className="mt-0.5 truncate text-[11px] text-slate-400">{hint}</p>
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
        <tr key={r} className="divide-x-0">
          {Array.from({ length: cols }).map((_, c) => (
            <td key={c} className="px-4 py-4">
              <div
                className="h-3.5 animate-pulse rounded bg-slate-100"
                style={{ width: `${55 + ((r * 13 + c * 7) % 35)}%` }}
              />
            </td>
          ))}
        </tr>
      ))}
    </tbody>
  );
}
