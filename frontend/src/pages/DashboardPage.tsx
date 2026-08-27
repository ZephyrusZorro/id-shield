import { Link } from "react-router-dom";
import {
  Files,
  CheckCircle2,
  AlertTriangle,
  ShieldAlert,
  Gauge,
  Plus,
} from "lucide-react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { MetricCard, SkeletonRows } from "../components/dashboard/MetricCard";
import { StatusBadge, statusToBadge } from "../components/dashboard/StatusBadge";
import { EmptyState } from "../components/layout/PageHeader";
import { useApi } from "../hooks/useApi";
import type { DashboardSummary, RecentScreeningsResponse } from "../types/api";

const DONUT_COLORS: Record<string, string> = {
  Valid: "#059669",
  Review: "#D97706",
  "High Risk": "#DC2626",
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
    <div className="mx-auto max-w-7xl animate-fade-in">
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
          label="Valid"
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
        <p role="alert" className="mt-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
          Could not load dashboard data: {summary.error ?? recent.error}
        </p>
      )}

      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-3">
        {/* Recent screenings */}
        <section className="card xl:col-span-2" aria-labelledby="recent-heading">
          <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
            <h3 id="recent-heading" className="text-sm font-bold text-navy-900">
              Recent Screenings
            </h3>
            <Link
              to="/history"
              className="text-xs font-semibold text-blue-600 hover:text-blue-700"
            >
              View all
            </Link>
          </div>

          {recent.loading ? (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[560px]">
                <thead className="border-b border-slate-100 bg-slate-50/60">
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
          ) : recent.data && recent.data.items.length > 0 ? (            <div className="overflow-x-auto">
              <table className="w-full min-w-[560px]">
                <thead className="border-b border-slate-100 bg-slate-50/60">
                  <tr>
                    <th scope="col" className="table-head-cell">Case ID</th>
                    <th scope="col" className="table-head-cell">Document Type</th>
                    <th scope="col" className="table-head-cell">Name</th>
                    <th scope="col" className="table-head-cell">Risk</th>
                    <th scope="col" className="table-head-cell">Status</th>
                    <th scope="col" className="table-head-cell">Time</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {recent.data.items.map((item) => (
                    <tr key={item.case_id} className="transition-colors hover:bg-slate-50/70">
                      <td className="table-cell font-semibold text-navy-900">
                        <Link
                          to={`/cases/${item.case_id}`}
                          className="text-blue-600 hover:text-blue-700 hover:underline"
                        >
                          #{item.case_number}
                        </Link>
                      </td>
                      <td className="table-cell">{item.document_type ?? "—"}</td>
                      <td className="table-cell">{item.person_name ?? item.case_name}</td>
                      <td className="table-cell">
                        {item.risk_score !== null ? (
                          <span
                            className={`font-bold ${
                              item.risk_score >= 60
                                ? "text-red-600"
                                : item.risk_score >= 30
                                  ? "text-amber-600"
                                  : "text-emerald-600"
                            }`}
                          >
                            {item.risk_score}
                          </span>
                        ) : (
                          "—"
                        )}
                      </td>
                      <td className="table-cell">
                        <StatusBadge status={statusToBadge(item.status)} />
                      </td>
                      <td className="table-cell whitespace-nowrap text-slate-400">
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
          <div className="border-b border-slate-100 px-5 py-4">
            <h3 id="distribution-heading" className="text-sm font-bold text-navy-900">
              Risk Distribution
            </h3>
          </div>
          <div className="flex flex-1 items-center justify-center p-4">
            {donutData.length > 0 ? (
              <>
                <ResponsiveContainer width="100%" height={240}>
                  <PieChart>
                    <Pie
                      data={donutData}
                      dataKey="value"
                      nameKey="name"
                      innerRadius={60}
                      outerRadius={90}
                      paddingAngle={3}
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
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
                <ul className="-ml-8 space-y-2 self-center">
                  {donutData.map((d) => (
                    <li key={d.name} className="flex items-center gap-2 text-xs">
                      <span
                        className="h-2.5 w-2.5 rounded-full"
                        style={{ backgroundColor: DONUT_COLORS[d.name] }}
                        aria-hidden="true"
                      />
                      <span className="font-medium text-slate-600">{d.name}</span>
                      <span className="font-bold text-navy-900">{d.value}</span>
                    </li>
                  ))}
                </ul>
              </>
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
