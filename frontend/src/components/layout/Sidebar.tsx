import { NavLink } from "react-router-dom";
import { ShieldCheck } from "lucide-react";
import { NAV_MAIN, NAV_SECONDARY, type NavItem } from "./navItems";

function NavButton({ item }: { item: NavItem }) {
  const Icon = item.icon;
  return (
    <NavLink
      to={item.to}
      title={item.label}
      className={({ isActive }) =>
        `group relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-xs font-semibold transition-all duration-150 lg:justify-start justify-center ${
          isActive
            ? "bg-gradient-to-r from-blue-600/90 to-blue-700 text-white shadow-glow-blue"
            : "text-slate-400 hover:bg-slate-800/60 hover:text-slate-100"
        }`
      }
    >
      {({ isActive }) => (
        <>
          <Icon
            size={17}
            strokeWidth={isActive ? 2.3 : 1.8}
            aria-hidden="true"
            className={`shrink-0 transition-transform duration-150 group-hover:scale-110 ${
              isActive ? "text-white" : "text-slate-400 group-hover:text-blue-400"
            }`}
          />
          <span className="hidden lg:inline">{item.label}</span>
          {isActive && (
            <span className="absolute left-0 top-1.5 bottom-1.5 w-1 rounded-r-full bg-blue-400 hidden lg:block" />
          )}
        </>
      )}
    </NavLink>
  );
}

export function Sidebar() {
  return (
    <aside className="hidden h-screen w-16 shrink-0 flex-col border-r border-slate-800/80 bg-[#070B14] md:flex lg:w-60 transition-all duration-200">
      {/* Brand */}
      <div className="flex items-center gap-3 px-3 pb-4 pt-5 lg:px-4">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-tr from-blue-600 via-indigo-600 to-blue-400 shadow-glow-blue">
          <ShieldCheck size={22} className="text-white" aria-hidden="true" />
        </div>
        <div className="hidden min-w-0 lg:block">
          <div className="flex items-center gap-1.5">
            <span className="text-sm font-extrabold tracking-wider text-white">
              ID-SHIELD
            </span>
            <span className="rounded bg-blue-500/20 px-1 py-0.2 text-[9px] font-bold text-blue-400">
              v0.1
            </span>
          </div>
          <p className="text-[10px] font-medium tracking-tight text-slate-400">
            Forensics Intelligence
          </p>
        </div>
      </div>

      <div className="mx-3 border-t border-slate-800/80 lg:mx-4" />

      {/* Navigation */}
      <nav
        aria-label="Primary"
        className="flex flex-1 flex-col gap-1 overflow-y-auto px-2 py-3 lg:px-3"
      >
        <div className="px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-slate-500 hidden lg:block">
          Core Operations
        </div>
        {NAV_MAIN.map((item) => (
          <NavButton key={item.to} item={item} />
        ))}

        <div className="my-2 border-t border-slate-800/80" />

        <div className="px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-slate-500 hidden lg:block">
          Platform & Diagnostics
        </div>
        {NAV_SECONDARY.map((item) => (
          <NavButton key={item.to} item={item} />
        ))}
      </nav>

      {/* Footer / Verifier Profile */}
      <div className="border-t border-slate-800/80 p-2 lg:p-3">
        <div className="flex items-center justify-center gap-2.5 rounded-lg bg-slate-900/60 p-1.5 lg:justify-start border border-slate-800/60">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-blue-600 text-xs font-bold text-white shadow-sm">
            AV
          </div>
          <div className="hidden min-w-0 flex-1 lg:block">
            <p className="truncate text-xs font-semibold text-white">
              A. Verifier
            </p>
            <p className="text-[10px] text-emerald-400 flex items-center gap-1">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
              Officer · Level 3
            </p>
          </div>
        </div>
      </div>
    </aside>
  );
}
