import { useState, useEffect } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { ApiStatus } from "./ApiStatus";
import { MobileDrawer } from "./MobileDrawer";
import { CalendarDays, Menu, Moon, ShieldCheck, Sun, Search, Command } from "lucide-react";
import { useTheme } from "../../context/ThemeContext";
import { CommandPalette } from "../common/CommandPalette";

const PAGE_META: Record<string, { title: string; subtitle: string }> = {
  "/dashboard": {
    title: "Dashboard",
    subtitle: "Identity screening operations & risk telemetry",
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
    title: "Verification Reports",
    subtitle: "Compliance dossiers and audit logs",
  },
  "/analytics": {
    title: "Forensic Analytics",
    subtitle: "Tampering trends and risk factor distribution",
  },
  "/users": {
    title: "User Management",
    subtitle: "Verifier accounts and security roles",
  },
  "/settings": {
    title: "Platform Diagnostics",
    subtitle: "Pipeline calibration & forensic engine status",
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
  const { theme, toggleTheme } = useTheme();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);

  const base = "/" + location.pathname.split("/").filter(Boolean)[0];
  const meta =
    PAGE_META[base] ??
    (location.pathname.startsWith("/cases")
      ? { title: "Case Dossier", subtitle: "Forensic evidence and multi-modal analysis workspace" }
      : location.pathname.startsWith("/screen/processing")
        ? { title: "Document Pipeline", subtitle: "Live 11-stage forensic screening progress" }
        : { title: "ID-SHIELD", subtitle: "Identity & Document Forensics" });

  // Global keyboard shortcut for Command Palette (Ctrl+K or Cmd+K)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setCommandPaletteOpen((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50 dark:bg-[#070B14] text-slate-900 dark:text-slate-100 transition-colors duration-200">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-blue-600 focus:px-4 focus:py-2 focus:text-sm focus:font-semibold focus:text-white"
        >
          Skip to main content
        </a>
        <header className="flex h-16 shrink-0 items-center justify-between gap-3 border-b border-slate-200/90 dark:border-slate-800/80 bg-white/90 dark:bg-[#0B1120]/90 backdrop-blur-md px-4 sm:px-6 transition-colors duration-200">
          <div className="flex min-w-0 items-center gap-3">
            {/* Mobile menu */}
            <button
              type="button"
              onClick={() => setDrawerOpen(true)}
              aria-label="Open navigation menu"
              className="rounded-lg p-2 text-slate-700 dark:text-slate-300 transition-colors hover:bg-slate-100 dark:hover:bg-slate-800 md:hidden"
            >
              <Menu size={22} aria-hidden="true" />
            </button>
            <div className="flex items-center gap-2 md:hidden">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 shadow-glow-blue">
                <ShieldCheck size={18} className="text-white" aria-hidden="true" />
              </div>
              <span className="text-sm font-bold tracking-wider text-slate-900 dark:text-white">ID-SHIELD</span>
            </div>
            <div className="hidden min-w-0 md:block">
              <h1 className="truncate text-base font-extrabold leading-tight text-slate-900 dark:text-white">
                {meta.title}
              </h1>
              <p className="truncate text-xs text-slate-500 dark:text-slate-400 font-medium">{meta.subtitle}</p>
            </div>
          </div>

          {/* Center / Right: Quick Search Button & Actions */}
          <div className="flex shrink-0 items-center gap-2.5">
            {/* Command Palette Trigger Button */}
            <button
              type="button"
              onClick={() => setCommandPaletteOpen(true)}
              className="hidden sm:flex items-center gap-2 rounded-xl border border-slate-200/90 dark:border-slate-800 bg-slate-100/70 dark:bg-slate-900/60 px-3 py-1.5 text-xs text-slate-500 dark:text-slate-400 transition-all hover:border-blue-400 dark:hover:border-blue-500 hover:text-slate-900 dark:hover:text-white hover:shadow-sm"
              title="Search commands and cases (Ctrl + K)"
            >
              <Search size={14} className="text-slate-400 dark:text-slate-500" />
              <span className="font-medium">Quick search...</span>
              <kbd className="inline-flex items-center gap-0.5 rounded border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-1.5 py-0.5 text-[10px] font-mono text-slate-600 dark:text-slate-300">
                <Command size={10} /> K
              </kbd>
            </button>

            {/* Theme Toggle Button */}
            <button
              type="button"
              onClick={toggleTheme}
              title={`Switch to ${theme === "dark" ? "Light" : "Dark"} Mode`}
              aria-label="Toggle theme"
              className="group relative flex h-9 w-9 items-center justify-center rounded-xl border border-slate-200/90 dark:border-slate-800 bg-white dark:bg-slate-900/80 text-slate-700 dark:text-slate-300 transition-all duration-200 hover:border-blue-400 dark:hover:border-blue-500 hover:text-blue-600 dark:hover:text-blue-400 hover:shadow-sm"
            >
              {theme === "dark" ? (
                <Sun size={17} className="transition-transform duration-300 group-hover:rotate-45 text-amber-400" aria-hidden="true" />
              ) : (
                <Moon size={17} className="transition-transform duration-300 group-hover:-rotate-12 text-slate-700" aria-hidden="true" />
              )}
            </button>

            {/* Date Pill */}
            <div className="hidden items-center gap-2 rounded-xl border border-slate-200/90 dark:border-slate-800 bg-white dark:bg-slate-900/60 px-3 py-1.5 lg:flex">
              <CalendarDays size={13} className="text-slate-400 dark:text-slate-500" aria-hidden="true" />
              <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                {formatDate(new Date())}
              </span>
            </div>

            <ApiStatus />
          </div>
        </header>

        <main
          id="main-content"
          className="flex-1 overflow-y-auto px-4 py-5 sm:px-6 sm:py-6"
        >
          <div key={location.pathname} className="animate-fade-in">
            <Outlet />
          </div>
        </main>

        <footer className="shrink-0 border-t border-slate-200/80 dark:border-slate-800/80 bg-white/80 dark:bg-[#0B1120]/80 backdrop-blur-sm px-4 py-2 sm:px-6 transition-colors duration-200">
          <p className="text-center text-[10px] leading-relaxed text-slate-400 dark:text-slate-500 sm:text-[11px] font-medium">
            ID-SHIELD Prototype · Assisted Multi-Modal Identity Forensics · Smart India Hackathon 2026
          </p>
        </footer>
      </div>

      <CommandPalette isOpen={commandPaletteOpen} onClose={() => setCommandPaletteOpen(false)} />
      <MobileDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} />
    </div>
  );
}
