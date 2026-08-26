import { useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { ApiStatus } from "./ApiStatus";
import { MobileDrawer } from "./MobileDrawer";
import { CalendarDays, Menu, ShieldCheck } from "lucide-react";

const PAGE_META: Record<string, { title: string; subtitle: string }> = {
  "/dashboard": {
    title: "Dashboard",
    subtitle: "Identity screening operations overview",
  },
  "/screen/new": {
    title: "Screen Documents",
    subtitle: "Create a case and upload identity evidence",
  },
  "/history": {
    title: "Screening History",
    subtitle: "Previously processed verification cases",
  },
  "/reports": {
    title: "Reports",
    subtitle: "Generated verification reports",
  },
  "/analytics": {
    title: "Analytics",
    subtitle: "Screening trends and risk factor statistics",
  },
  "/users": {
    title: "User Management",
    subtitle: "Verifier accounts and access roles",
  },
  "/settings": {
    title: "Settings",
    subtitle: "Platform configuration",
  },
};

function formatDate(d: Date) {
  return d.toLocaleDateString(undefined, {
    weekday: "short",
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function AppLayout() {
  const location = useLocation();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const base = "/" + location.pathname.split("/").filter(Boolean)[0];
  const meta =
    PAGE_META[base] ??
    (location.pathname.startsWith("/cases")
      ? { title: "Case Detail", subtitle: "Verification evidence workspace" }
      : location.pathname.startsWith("/screen/processing")
        ? { title: "Screen Documents", subtitle: "Live pipeline progress" }
        : { title: "ID-SHIELD", subtitle: "" });

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-blue-600 focus:px-4 focus:py-2 focus:text-sm focus:font-semibold focus:text-white"
        >
          Skip to main content
        </a>
        <header className="flex h-16 shrink-0 items-center justify-between gap-3 border-b border-slate-200 bg-white px-4 sm:px-6">
          <div className="flex min-w-0 items-center gap-3">
            {/* Mobile menu */}
            <button
              type="button"
              onClick={() => setDrawerOpen(true)}
              aria-label="Open navigation menu"
              className="rounded-lg p-2 text-navy-800 transition-colors hover:bg-slate-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-600 md:hidden"
            >
              <Menu size={22} aria-hidden="true" />
            </button>
            <div className="flex items-center gap-2 md:hidden">
              <ShieldCheck size={20} className="text-blue-600" aria-hidden="true" />
              <span className="text-sm font-bold tracking-wide text-navy-900">ID-SHIELD</span>
            </div>
            <div className="hidden min-w-0 md:block">
              <h1 className="truncate text-lg font-bold leading-tight text-navy-900">
                {meta.title}
              </h1>
              <p className="truncate text-xs text-slate-500">{meta.subtitle}</p>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-3">
            <div className="hidden items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1.5 lg:flex">
              <CalendarDays size={14} className="text-slate-400" aria-hidden="true" />
              <span className="text-xs font-medium text-slate-600">
                {formatDate(new Date())}
              </span>
            </div>
            <ApiStatus />
          </div>
        </header>

        <main
          id="main-content"
          className="flex-1 overflow-y-auto px-6 py-6"
        >
          <div key={location.pathname} className="animate-fade-in">
            <Outlet />
          </div>
        </main>

        <footer className="shrink-0 border-t border-slate-200 bg-white px-4 py-2.5 sm:px-6">
          <p className="text-center text-[10px] leading-relaxed text-slate-400 sm:text-[11px]">
            ID-SHIELD prototype for assisted identity verification. Final
            verification decisions must be made by authorized human personnel.
            Demo data is synthetic.
          </p>
        </footer>
      </div>

      <MobileDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} />
    </div>
  );
}
