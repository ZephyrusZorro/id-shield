import { PageHeader } from "../components/layout/PageHeader";
import { Shield, UserCheck, Key, Plus, CheckCircle2 } from "lucide-react";

interface VerifierUser {
  id: string;
  name: string;
  email: string;
  role: "Lead Forensic Officer" | "Compliance Auditor" | "Level 2 Analyst" | "System Admin";
  casesProcessed: number;
  status: "Active" | "Standby";
  lastActive: string;
}

const DEMO_USERS: VerifierUser[] = [
  {
    id: "usr-01",
    name: "Arjun Verifier",
    email: "arjun.verifier@idshield.gov",
    role: "Lead Forensic Officer",
    casesProcessed: 142,
    status: "Active",
    lastActive: "Just now",
  },
  {
    id: "usr-02",
    name: "Priya Sundaram",
    email: "priya.s@idshield.gov",
    role: "Compliance Auditor",
    casesProcessed: 89,
    status: "Active",
    lastActive: "15m ago",
  },
  {
    id: "usr-03",
    name: "Vikram Malhotra",
    email: "vikram.m@idshield.gov",
    role: "Level 2 Analyst",
    casesProcessed: 64,
    status: "Active",
    lastActive: "1h ago",
  },
  {
    id: "usr-04",
    name: "System Administrator",
    email: "admin@idshield.gov",
    role: "System Admin",
    casesProcessed: 210,
    status: "Active",
    lastActive: "Yesterday",
  },
];

export function UsersPage() {
  return (
    <div className="mx-auto max-w-6xl animate-fade-in space-y-6 pb-12">
      <PageHeader
        title="User &amp; Access Management"
        subtitle="Verifier credentials, RBAC security privileges, and audit permissions"
        actions={
          <button
            type="button"
            className="btn-primary shadow-glow-blue flex items-center gap-1.5 text-xs"
          >
            <Plus size={14} />
            <span>Invite Verifier</span>
          </button>
        }
      />

      {/* Role Summary Badges */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="card p-4 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50 dark:bg-blue-950/80 text-blue-600 dark:text-blue-400">
            <UserCheck size={20} />
          </div>
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">Active Verifiers</p>
            <p className="text-xl font-extrabold text-navy-900 dark:text-white">4 Officers</p>
          </div>
        </div>

        <div className="card p-4 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-50 dark:bg-emerald-950/80 text-emerald-600 dark:text-emerald-400">
            <Shield size={20} />
          </div>
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">Role Policies</p>
            <p className="text-xl font-extrabold text-navy-900 dark:text-white">RBAC Strict</p>
          </div>
        </div>

        <div className="card p-4 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-purple-50 dark:bg-purple-950/80 text-purple-600 dark:text-purple-400">
            <Key size={20} />
          </div>
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">Audit Logging</p>
            <p className="text-xl font-extrabold text-navy-900 dark:text-white">Immutable Ledger</p>
          </div>
        </div>
      </div>

      {/* Users Table */}
      <div className="card overflow-hidden">
        <div className="border-b border-slate-100 dark:border-slate-800 px-5 py-4 flex items-center justify-between">
          <h3 className="text-xs font-bold uppercase tracking-wider text-navy-900 dark:text-white">
            Authorized Personnel Directory
          </h3>
          <span className="text-[11px] text-slate-400 font-mono">4 Accounts Registered</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead className="border-b border-slate-100 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-900/60 text-slate-500 dark:text-slate-400">
              <tr>
                <th className="px-4 py-3 text-left font-bold uppercase tracking-wider">Officer</th>
                <th className="px-4 py-3 text-left font-bold uppercase tracking-wider">Assigned Role</th>
                <th className="px-4 py-3 text-left font-bold uppercase tracking-wider">Dossiers Handled</th>
                <th className="px-4 py-3 text-left font-bold uppercase tracking-wider">Security State</th>
                <th className="px-4 py-3 text-left font-bold uppercase tracking-wider">Last Activity</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/80">
              {DEMO_USERS.map((u) => (
                <tr key={u.id} className="hover:bg-slate-50/70 dark:hover:bg-slate-800/40 transition-colors">
                  <td className="px-4 py-3.5">
                    <div className="font-bold text-navy-900 dark:text-white">{u.name}</div>
                    <div className="text-[11px] text-slate-400 dark:text-slate-500 font-mono">{u.email}</div>
                  </td>
                  <td className="px-4 py-3.5">
                    <span className="inline-flex items-center gap-1 rounded-md bg-blue-50 dark:bg-blue-950/60 px-2 py-0.5 text-[11px] font-semibold text-blue-700 dark:text-blue-400 border border-blue-100 dark:border-blue-800/40">
                      {u.role}
                    </span>
                  </td>
                  <td className="px-4 py-3.5 font-mono font-bold text-slate-700 dark:text-slate-300">
                    {u.casesProcessed} cases
                  </td>
                  <td className="px-4 py-3.5">
                    <span className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-600 dark:text-emerald-400">
                      <CheckCircle2 size={13} />
                      {u.status}
                    </span>
                  </td>
                  <td className="px-4 py-3.5 text-slate-400 dark:text-slate-500 text-[11px]">
                    {u.lastActive}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
