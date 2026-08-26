import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Loader2, Search, ArrowUpDown, Plus } from "lucide-react";
import { PageHeader, EmptyState } from "../components/layout/PageHeader";
import { StatusBadge, statusToBadge } from "../components/dashboard/StatusBadge";
import { useApi } from "../hooks/useApi";
import type { HistoryItem } from "../types/api";

type SortKey = "recent" | "risk_desc" | "risk_asc";

const OUTCOME_FILTERS = [
  { value: "all", label: "All outcomes" },
  { value: "valid", label: "Valid" },
  { value: "review", label: "Review" },
  { value: "high_risk", label: "High Risk" },
  { value: "unable", label: "Unable to verify" },
];

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function recommendationToStatus(rec: string | null, risk: number | null) {
  if (rec === null || risk === null || rec === "unable_to_verify")
    return rec === "unable_to_verify" ? "pending" : "processing";
  if (rec === "verification_passed") return "valid";
  if (risk >= 60) return "high_risk";
  return "under_review";
}

export function HistoryPage() {
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [outcome, setOutcome] = useState("all");
  const [sort, setSort] = useState<SortKey>("recent");

  // Debounce search so we don't hit the API on every keystroke.
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search.trim()), 300);
    return () => clearTimeout(t);
  }, [search]);

  const query = `/api/cases?search=${encodeURIComponent(debouncedSearch)}&outcome=${outcome}&sort=${sort}`;
  const { data, loading, error } = useApi<HistoryItem[]>(query);

  const items = useMemo(() => data ?? [], [data]);

  return (
    <div className="mx-auto max-w-6xl animate-fade-in">
      <PageHeader
        title="Screening History"
        subtitle="Previously processed verification cases"
        actions={
          <Link to="/screen/new" className="btn-primary">
            <Plus size={16} aria-hidden="true" /> New Case
          </Link>
        }
      />

      {/* Controls */}
      <div className="card mb-4 flex flex-wrap items-center gap-3 p-4">
        <div className="relative min-w-[220px] flex-1">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" aria-hidden="true" />
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by name, case name or case number…"
            aria-label="Search screening history"
            className="input-field pl-9"
          />
        </div>
        <select
          value={outcome}
          onChange={(e) => setOutcome(e.target.value)}
          aria-label="Filter by outcome"
          className="input-field w-auto"
        >
          {OUTCOME_FILTERS.map((f) => (
            <option key={f.value} value={f.value}>
              {f.label}
            </option>
          ))}
        </select>
        <select
          value={sort}
          onChange={(e) => setSort(e.target.value as SortKey)}
          aria-label="Sort cases"
          className="input-field w-auto"
        >
          <option value="recent">Newest first</option>
          <option value="risk_desc">Risk: high to low</option>
          <option value="risk_asc">Risk: low to high</option>
        </select>
      </div>

      {error && (
        <p role="alert" className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </p>
      )}

      <div className="card overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center gap-3 py-16 text-sm text-slate-500">
            <Loader2 size={18} className="animate-spin" aria-hidden="true" /> Loading history…
          </div>
        ) : items.length === 0 ? (
          <EmptyState
            title="No matching screenings"
            message={
              search || outcome !== "all"
                ? "Try adjusting the search or filters."
                : "Screen a set of documents to create your first case."
            }
            action={
              !search && outcome === "all" ? (
                <Link to="/screen/new" className="btn-primary">
                  <Plus size={16} aria-hidden="true" /> New Case
                </Link>
              ) : undefined
            }
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px]">
              <thead className="border-b border-slate-100 bg-slate-50/60">
                <tr>
                  <th scope="col" className="table-head-cell">
                    <span className="inline-flex items-center gap-1">
                      Case <ArrowUpDown size={12} aria-hidden="true" />
                    </span>
                  </th>
                  <th scope="col" className="table-head-cell">Subject</th>
                  <th scope="col" className="table-head-cell">Case Name</th>
                  <th scope="col" className="table-head-cell">Docs</th>
                  <th scope="col" className="table-head-cell">
                    <span className="inline-flex items-center gap-1">
                      Risk <ArrowUpDown size={12} aria-hidden="true" />
                    </span>
                  </th>
                  <th scope="col" className="table-head-cell">Status</th>
                  <th scope="col" className="table-head-cell">Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {items.map((item) => (
                  <tr key={item.id} className="transition-colors hover:bg-slate-50/70">
                    <td className="table-cell font-semibold">
                      <Link
                        to={`/cases/${item.id}`}
                        className="text-blue-600 hover:text-blue-700 hover:underline"
                      >
                        #{item.case_number}
                      </Link>
                    </td>
                    <td className="table-cell">{item.person_name ?? "—"}</td>
                    <td className="table-cell max-w-[220px] truncate">{item.case_name}</td>
                    <td className="table-cell">{item.document_count}</td>
                    <td className="table-cell">
                      {item.overall_risk !== null ? (
                        <span
                          className={`font-bold ${
                            item.overall_risk >= 60
                              ? "text-red-600"
                              : item.overall_risk >= 30
                                ? "text-amber-600"
                                : "text-emerald-600"
                          }`}
                        >
                          {item.overall_risk}
                        </span>
                      ) : (
                        <span className="text-slate-400">—</span>
                      )}
                    </td>
                    <td className="table-cell">
                      <StatusBadge
                        status={statusToBadge(
                          recommendationToStatus(item.recommendation, item.overall_risk)
                        )}
                      />
                    </td>
                    <td className="table-cell whitespace-nowrap text-slate-400">
                      {fmtDate(item.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <p className="mt-3 text-center text-[11px] text-slate-400">
        All entries derive from synthetic demo submissions.
      </p>
    </div>
  );
}
