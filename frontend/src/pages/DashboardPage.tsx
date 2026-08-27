import { Link } from "react-router-dom";
import {
  Files,
  CheckCircle2,
  AlertTriangle,
  ShieldAlert,
  Gauge,
  Plus,
  ArrowRight,
  Sparkles,
} from "lucide-react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { MetricCard, SkeletonRows } from "../components/dashboard/MetricCard";
import { StatusBadge, statusToBadge } from "../components/dashboard/StatusBadge";
import { EmptyState } from "../components/layout/PageHeader";
import { useApi } from "../hooks/useApi";
import type { DashboardSummary, RecentScreeningsResponse } from "../types/api";

const DONUT_COLORS: Record<string, string> = {
  Valid: "#10B981",
  Review: "#F59E0B",
  "High Risk": "#EF4444",
};

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export function DashboardPage() {
  const summary = useApi<DashboardSummary>("/api/dashboard/summary");
  const recent = useApi<RecentScreeningsResponse>("/api/dashboard/recent");

  const s = summary.data;
  const donutData =
    s === null
      ? []
      : [
          { name: "Valid", value: s.valid },
          { name: "Review", value: s.under_review },
          { name: "High Risk", value: s.high_risk },
        ].filter((d) => d.value > 0);

  return (
    <div className="mx-auto max-w-7xl animate-fade-in space-y-6">
      {/* Top Banner with Quick Actions */}
      <div className="card relative overflow-hidden p-5 sm:p-6 bg-gradient-to-r from-blue-900/10 via-indigo-900/10 to-slate-900/10 dark:from-blue-950/40 dark:via-indigo-950/30 dark:to-dark-surface border-blue-200/40 dark:border-blue-900/40">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1 rounded-full bg-blue-500/10 dark:bg-blue-500/20 px-2.5 py-0.5 text-xs font-semibold text-blue-600 dark:text-blue-400">
                <Sparkles size={13} aria-hidden="true" />
                Live Verification Engine Active
              </span>
            </div>
            <h2 className="mt-2 text-xl font-extrabold text-navy-900 dark:text-white">
              Identity Forensics Operations Hub
            </h2>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400 max-w-xl">
              11-stage automated screening evaluating ICAO MRZ integrity, visual tampering ELA, facial biometrics, and multi-document consistency.
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-3">
            <Link
              to="/screen/new"
              className="btn-primary flex items-center gap-1.5 shadow-glow-blue"
            >
              <Plus size={16} aria-hidden="true" />
              <span>Screen New Document</span>
            </Link>
          </div>
        </div>
      </div>

      {/* Metric cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <MetricCard
          label="Total Screened"
          value={s?.total_screened ?? "—"}
          icon={Files}
          tone="navy"
          loading={summary.loading}
        />
        <MetricCard
          label="Valid / Passed"
          value={s?.valid ?? "—"}
          icon={CheckCircle2}
          tone="green"
          loading={summary.loading}
        />
        <MetricCard
          label="Under Review"
          value={s?.under_review ?? "—"}
          icon={AlertTriangle}
          tone="amber"
          loading={summary.loading}
        />
        <MetricCard
          label="High Risk"
          value={s?.high_risk ?? "—"}
          icon={ShieldAlert}
          tone="red"
          loading={summary.loading}
        />
        <MetricCard
          label="Avg Risk Score"
          value={s ? (s.average_risk_score ?? "—") : "—"}
          icon={Gauge}
          tone="blue"
          loading={summary.loading}
        />
      </div>

      {(summary.error || recent.error) && (
        <p role="alert" className="rounded-lg bg-rose-50 dark:bg-rose-950/60 p-4 text-xs font-semibold text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800">
          Could not load telemetry: {summary.error ?? recent.error}
        </p>
      )}

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        {/* Recent screenings */}
        <section className="card xl:col-span-2 overflow-hidden" aria-labelledby="recent-heading">
          <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800/80 px-5 py-4">
            <h3 id="recent-heading" className="text-sm font-bold text-navy-900 dark:text-white flex items-center gap-2">
              Recent Verification Cases
            </h3>
            <Link
              to="/history"
              className="text-xs font-semibold text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1"
            >
              <span>View full history</span>
              <ArrowRight size={12} aria-hidden="true" />
            </Link>
          </div>

          {recent.loading ? (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[560px]">
                <thead className="border-b border-slate-100 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-900/40">
                  <tr>
                    <th scope="col" className="table-head-cell">Case ID</th>
                    <th scope="col" className="table-head-cell">Document Type</th>
                    <th scope="col" className="table-head-cell">Name</th>
                    <th scope="col" className="table-head-cell">Risk</th>
                    <th scope="col" className="table-head-cell">Status</th>
                    <th scope="col" className="table-head-cell">Time</th>
                  </tr>
                </thead>
                <SkeletonRows rows={4} cols={6} />
              </table>
            </div>
          ) : recent.data && recent.data.items.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[560px]">
                <thead className="border-b border-slate-100 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-900/40">
                  <tr>
                    <th scope="col" className="table-head-cell">Case ID</th>
                    <th scope="col" className="table-head-cell">Document Type</th>
                    <th scope="col" className="table-head-cell">Name</th>
                    <th scope="col" className="table-head-cell">Risk</th>
                    <th scope="col" className="table-head-cell">Status</th>
                    <th scope="col" className="table-head-cell">Time</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800/80">
                  {recent.data.items.map((item) => (
                    <tr key={item.case_id} className="transition-colors hover:bg-slate-50/80 dark:hover:bg-slate-800/50">
                      <td className="table-cell font-mono font-bold text-navy-900 dark:text-white">
                        <Link
                          to={`/cases/${item.case_id}`}
                          className="text-blue-600 dark:text-blue-400 hover:underline"
                        >
                          #{item.case_number}
                        </Link>
                      </td>
                      <td className="table-cell text-slate-600 dark:text-slate-300 font-medium">
                        {item.document_type ?? "—"}
                      </td>
                      <td className="table-cell font-semibold text-slate-800 dark:text-slate-200">
                        {item.person_name ?? item.case_name}
                      </td>
                      <td className="table-cell">
                        {item.risk_score !== null ? (
                          <span
                            className={`font-mono font-extrabold ${
                              item.risk_score >= 60
                                ? "text-rose-600 dark:text-rose-400"
                                : item.risk_score >= 30
                                  ? "text-amber-600 dark:text-amber-400"
                                  : "text-emerald-600 dark:text-emerald-400"
                            }`}
                          >
                            {item.risk_score}/100
                          </span>
                        ) : (
                          "—"
                        )}
                      </td>
                      <td className="table-cell">
                        <StatusBadge status={statusToBadge(item.status)} />
                      </td>
                      <td className="table-cell whitespace-nowrap text-slate-400 dark:text-slate-500 text-xs">
                        {timeAgo(item.created_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState
              title="No screenings yet"
              message="Create your first case to begin screening identity documents."
              action={
                <Link to="/screen/new" className="btn-primary">
                  <Plus size={16} aria-hidden="true" /> New Case
                </Link>
              }
            />
          )}
        </section>

        {/* Risk distribution */}
        <section className="card flex flex-col" aria-labelledby="distribution-heading">
          <div className="border-b border-slate-100 dark:border-slate-800/80 px-5 py-4">
            <h3 id="distribution-heading" className="text-sm font-bold text-navy-900 dark:text-white">
              Risk Distribution Breakdown
            </h3>
          </div>
          <div className="flex flex-1 items-center justify-center p-4">
            {donutData.length > 0 ? (
              <div className="flex w-full items-center justify-around">
                <div className="h-56 w-56">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={donutData}
                        dataKey="value"
                        nameKey="name"
                        innerRadius={55}
                        outerRadius={80}
                        paddingAngle={4}
                        strokeWidth={0}
                      >
                        {donutData.map((entry) => (
                          <Cell
                            key={entry.name}
                            fill={DONUT_COLORS[entry.name]}
                            aria-hidden="true"
                          />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "#0F172A",
                          borderRadius: "8px",
                          border: "1px solid #334155",
                          color: "#fff",
                          fontSize: "12px",
                        }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <ul className="space-y-3">
                  {donutData.map((d) => (
                    <li key={d.name} className="flex items-center gap-2.5 text-xs">
                      <span
                        className="h-3 w-3 rounded-full shadow-sm"
                        style={{ backgroundColor: DONUT_COLORS[d.name] }}
                        aria-hidden="true"
                      />
                      <span className="font-medium text-slate-600 dark:text-slate-300">{d.name}</span>
                      <span className="font-bold text-navy-900 dark:text-white ml-auto">{d.value}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <EmptyState
                title={s && s.total_screened > 0 ? "All cases pending" : "No data yet"}
                message="Risk distribution appears once screening results exist."
              />
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
