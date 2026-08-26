import { PageHeader, EmptyState } from "../components/layout/PageHeader";

export function ReportsPage() {
  return (
    <div className="mx-auto max-w-6xl animate-fade-in">
      <PageHeader
        title="Reports"
        subtitle="Generated verification reports"
      />
      <div className="card">
        <EmptyState
          title="No reports generated yet"
          message="Completed screenings produce audit-friendly verification reports with full evidence citations."
        />
      </div>
    </div>
  );
}
