import { useState, useMemo } from "react";
import { Link } from "react-router-dom";
import {
  FileText,
  Search,
  ExternalLink,
  ShieldAlert,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Filter,
} from "lucide-react";
import { PageHeader, EmptyState } from "../components/layout/PageHeader";
import { StatusBadge } from "../components/dashboard/StatusBadge";
import { useApi } from "../hooks/useApi";
import type { HistoryItem, ScreeningStatus } from "../types/api";

function recommendationToStatus(rec: string | null, risk: number | null): ScreeningStatus {
  if (rec === null || risk === null || rec === "unable_to_verify")
    return "pending";
  if (rec === "verification_passed") return "valid";
  if (risk >= 60 || rec === "manual_review_required") return "high_risk";
  return "under_review";
}

export function ReportsPage() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const { data: cases, loading, error, reload } = useApi<HistoryItem[]>("/api/cases");

  const filteredReports = useMemo(() => {
    if (!cases) return [];
    return cases.filter((item) => {
      const matchesSearch =
        search === "" ||
        item.case_name.toLowerCase().includes(search.toLowerCase()) ||
        `#${item.case_number}`.includes(search) ||
        (item.person_name && item.person_name.toLowerCase().includes(search.toLowerCase()));

      const badgeStatus = recommendationToStatus(item.recommendation, item.overall_risk);
      const matchesStatus =
        statusFilter === "all" ||
        badgeStatus === statusFilter;

      return matchesSearch && matchesStatus;
    });
  }, [cases, search, statusFilter]);

  const stats = useMemo(() => {
    if (!cases) return { total: 0, valid: 0, review: 0, highRisk: 0 };
    return {
      total: cases.length,
      valid: cases.filter((c) => recommendationToStatus(c.recommendation, c.overall_risk) === "valid").length,
      review: cases.filter((c) => recommendationToStatus(c.recommendation, c.overall_risk) === "under_review").length,
      highRisk: cases.filter((c) => recommendationToStatus(c.recommendation, c.overall_risk) === "high_risk").length,
    };
  }, [cases]);


  return (
    <div className="mx-auto max-w-7xl animate-fade-in space-y-6 pb-12">
      <PageHeader
        title="Verification Reports"
        subtitle="Forensic evidence dossiers, compliance ledgers, and explainable audit reports"
        actions={
          <button
            type="button"
            onClick={reload}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 shadow-sm hover:bg-slate-50"
          >
            Refresh Reports
          </button>
        }
      />

      {/* Summary KPI Strip */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-4">
        <div className="card p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Total Reports</span>
            <FileText className="h-4 w-4 text-blue-600" />
          </div>
          <p className="mt-2 text-2xl font-bold text-navy-900">{stats.total}</p>
          <span className="text-[11px] text-slate-500">Generated audit records</span>
        </div>

        <div className="card p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Passed / Verified</span>
            <CheckCircle2 className="h-4 w-4 text-emerald-600" />
          </div>
          <p className="mt-2 text-2xl font-bold text-emerald-600">{stats.valid}</p>
          <span className="text-[11px] text-slate-500">Consistent evidence sets</span>
        </div>

        <div className="card p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Under Review</span>
            <AlertTriangle className="h-4 w-4 text-amber-600" />
          </div>
          <p className="mt-2 text-2xl font-bold text-amber-600">{stats.review}</p>
          <span className="text-[11px] text-slate-500">Requires secondary check</span>
        </div>

        <div className="card p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">High Risk</span>
            <ShieldAlert className="h-4 w-4 text-rose-600" />
          </div>
          <p className="mt-2 text-2xl font-bold text-rose-600">{stats.highRisk}</p>
          <span className="text-[11px] text-slate-500">Tampering / mismatch flagged</span>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search reports by case name, applicant or ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-lg border border-slate-200 bg-white py-2 pl-9 pr-3 text-xs shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>

        <div className="flex items-center gap-1 rounded-lg border border-slate-200 bg-white p-1 shadow-sm">
          <Filter className="ml-2 mr-1 h-3.5 w-3.5 text-slate-400" />
          {[
            { key: "all", label: "All" },
            { key: "valid", label: "Passed" },
            { key: "under_review", label: "Review" },
            { key: "high_risk", label: "High Risk" },
          ].map((tab) => (
            <button
              key={tab.key}
              type="button"
              onClick={() => setStatusFilter(tab.key)}
              className={`rounded-md px-3 py-1 text-xs font-medium transition-all ${
                statusFilter === tab.key
                  ? "bg-navy-900 text-white shadow-sm"
                  : "text-slate-600 hover:bg-slate-50"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Reports List / Table */}
      <div className="card overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-xs text-slate-400">Loading verification reports...</div>
        ) : error ? (
          <div className="p-6 text-center text-xs text-red-600">Failed to load reports: {error}</div>
        ) : filteredReports.length === 0 ? (
          <EmptyState
            title="No reports match your filter"
            message="Run a new screening or adjust your search filters above."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-100 bg-slate-50/75 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                <tr>
                  <th className="px-4 py-3">Case ID</th>
                  <th className="px-4 py-3">Applicant / Case Name</th>
                  <th className="px-4 py-3">Documents</th>
                  <th className="px-4 py-3">Risk Assessment</th>
                  <th className="px-4 py-3">Created</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredReports.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-50/60 transition-colors">
                    <td className="px-4 py-3.5 font-mono font-semibold text-blue-600">
                      #{item.case_number}
                    </td>
                    <td className="px-4 py-3.5">
                      <div className="font-semibold text-navy-900">{item.person_name || item.case_name}</div>
                      {item.person_name && (
                        <div className="text-[11px] text-slate-400">{item.case_name}</div>
                      )}
                    </td>
                    <td className="px-4 py-3.5 text-slate-600">
                      {item.document_count} {item.document_count === 1 ? "document" : "documents"}
                    </td>
                    <td className="px-4 py-3.5">
                      <div className="flex items-center gap-2">
                        <StatusBadge status={recommendationToStatus(item.recommendation, item.overall_risk)} />
                        {item.overall_risk !== null && (
                          <span className="text-[11px] font-medium text-slate-500">
                            Score: {item.overall_risk}/100
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3.5 text-slate-500">
                      <div className="flex items-center gap-1">
                        <Clock className="h-3 w-3 text-slate-400" />
                        <span>{new Date(item.created_at).toLocaleDateString()}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3.5 text-right space-x-2">
                      <Link
                        to={`/cases/${item.id}`}
                        className="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-2.5 py-1 text-[11px] font-semibold text-navy-900 shadow-sm hover:bg-slate-50"
                      >
                        <ExternalLink className="h-3 w-3 text-slate-400" />
                        <span>View Dossier</span>
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
