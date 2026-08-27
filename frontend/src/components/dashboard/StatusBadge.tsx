import { CheckCircle2, AlertTriangle, ShieldAlert, Clock, Loader2 } from "lucide-react";

export type BadgeKind =
  | "valid"
  | "under_review"
  | "high_risk"
  | "pending"
  | "processing";

const STYLES: Record<BadgeKind, string> = {
  valid: "bg-emerald-50 text-emerald-700 ring-emerald-600/20",
  under_review: "bg-amber-50 text-amber-700 ring-amber-600/25",
  high_risk: "bg-red-50 text-red-700 ring-red-600/20",
  pending: "bg-slate-100 text-slate-600 ring-slate-500/20",
  processing: "bg-blue-50 text-blue-700 ring-blue-600/20",
};

const LABELS: Record<BadgeKind, string> = {
  valid: "Valid",
  under_review: "Review",
  high_risk: "High Risk",
  pending: "Pending",
  processing: "Processing",
};

const ICONS: Record<BadgeKind, typeof CheckCircle2> = {
  valid: CheckCircle2,
  under_review: AlertTriangle,
  high_risk: ShieldAlert,
  pending: Clock,
  processing: Loader2,
};

/** Status badge — never relies on color alone (icon + text included). */
export function StatusBadge({ status }: { status: BadgeKind }) {
  const Icon = ICONS[status];
  return (
    <span
      className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${STYLES[status]}`}
    >
      <Icon size={13} aria-hidden="true" className={status === "processing" ? "animate-spin" : ""} />
      {LABELS[status]}
    </span>
  );
}

export function statusToBadge(status: string): BadgeKind {
  switch (status) {
    case "valid":
      return "valid";
    case "under_review":
      return "under_review";
    case "high_risk":
      return "high_risk";
    case "processing":
      return "processing";
    default:
      return "pending";
  }
}
