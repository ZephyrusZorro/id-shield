import { PageHeader, EmptyState } from "../components/layout/PageHeader";

export function UsersPage() {
  return (
    <div className="mx-auto max-w-6xl animate-fade-in">
      <PageHeader
        title="User Management"
        subtitle="Verifier accounts and access roles"
      />
      <div className="card">
        <EmptyState
          title="User management coming soon"
          message="Verifier accounts, roles and audit access will be managed from this page."
        />
      </div>
    </div>
  );
}
