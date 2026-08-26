import { NavLink } from "react-router-dom";
import { LogOut, ShieldCheck } from "lucide-react";
import { NAV_MAIN, NAV_SECONDARY, type NavItem } from "./navItems";

function NavButton({ item }: { item: NavItem }) {
  const Icon = item.icon;
  return (
    <NavLink
      to={item.to}
      title={item.label}
      className={({ isActive }) =>
        `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors lg:justify-start justify-center ${
          isActive
            ? "bg-navy-700 text-white"
            : "text-navy-200 hover:bg-navy-800 hover:text-white"
        }`
      }
    >
      <Icon size={18} strokeWidth={2} aria-hidden="true" className="shrink-0" />
      <span className="hidden lg:inline">{item.label}</span>
    </NavLink>
  );
}

export function Sidebar() {
  return (
    <aside className="hidden h-screen w-16 shrink-0 flex-col bg-navy-900 md:flex lg:w-64">
      {/* Brand */}
      <div className="flex items-center gap-3 px-3 pb-5 pt-6 lg:px-5">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-blue-600 shadow-card">
          <ShieldCheck size={22} className="text-white" aria-hidden="true" />
        </div>
        <div className="hidden min-w-0 lg:block">
          <p className="text-base font-bold leading-tight tracking-wide text-white">
            ID-SHIELD
          </p>
          <p className="text-[11px] leading-tight text-navy-300">
            Document Forensics
          </p>
        </div>
      </div>

      <div className="mx-3 border-t border-navy-700/60 lg:mx-5" />

      {/* Navigation */}
      <nav
        aria-label="Primary"
        className="flex flex-1 flex-col gap-1 overflow-y-auto px-2 py-4 lg:px-3"
      >
        {NAV_MAIN.map((item) => (
          <NavButton key={item.to} item={item} />
        ))}

        <div className="my-3 border-t border-navy-700/60" />

        {NAV_SECONDARY.map((item) => (
          <NavButton key={item.to} item={item} />
        ))}
      </nav>

      {/* Footer / user */}
      <div className="border-t border-navy-700/60 p-2 lg:p-3">
        <div className="flex items-center justify-center gap-3 px-2 py-1 lg:justify-start">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-navy-600 text-xs font-bold text-navy-100">
            AV
          </div>
          <div className="hidden min-w-0 flex-1 lg:block">
            <p className="truncate text-sm font-medium text-white">
              A. Verifier
            </p>
            <p className="text-[11px] text-navy-300">Verification Officer</p>
          </div>
          <button
            type="button"
            title="Log out (disabled in prototype)"
            aria-label="Log out"
            className="hidden rounded-lg p-2 text-navy-300 transition-colors hover:bg-navy-800 hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-500 lg:block"
          >
            <LogOut size={16} aria-hidden="true" />
          </button>
        </div>
      </div>
    </aside>
  );
}
