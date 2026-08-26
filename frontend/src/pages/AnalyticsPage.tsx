import { PageHeader, EmptyState } from "../components/layout/PageHeader";

export function AnalyticsPage() {
  return (
    <div className="mx-auto max-w-6xl animate-fade-in">
      <PageHeader
        title="Analytics"
        subtitle="Screening trends and risk factor statistics (demo data)"
      />
      <div className="card">
        <EmptyState
          title="Analytics coming soon"
          message="Case volumes, common mismatch fields, processing times and screening trends will be shown here."
        />
      </div>
    </div>
  );
}
