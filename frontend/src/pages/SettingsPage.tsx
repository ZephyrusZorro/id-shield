import { PageHeader, EmptyState } from "../components/layout/PageHeader";

export function SettingsPage() {
  return (
    <div className="mx-auto max-w-6xl animate-fade-in">
      <PageHeader
        title="Settings"
        subtitle="Platform configuration"
      />
      <div className="card">
        <EmptyState
          title="Settings coming soon"
          message="Risk weight configuration, module toggles (face verification, MRZ) and data retention options will be managed here."
        />
      </div>
    </div>
  );
}
