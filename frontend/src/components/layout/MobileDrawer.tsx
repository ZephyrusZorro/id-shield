import { useEffect } from "react";
import { NavLink } from "react-router-dom";
import { X, ShieldCheck, LogOut } from "lucide-react";
import { NAV_MAIN, NAV_SECONDARY, type NavItem } from "./navItems";

interface MobileDrawerProps {
  open: boolean;
  onClose: () => void;
}

function DrawerLink({ item, onClose }: { item: NavItem; onClose: () => void }) {
  const Icon = item.icon;
  return (
    <NavLink
      to={item.to}
      onClick={onClose}
      className={({ isActive }) =>
        `flex items-center gap-3 rounded-lg px-3 py-3 text-sm font-medium transition-colors ${
          isActive
            ? "bg-navy-700 text-white"
            : "text-navy-200 hover:bg-navy-800 hover:text-white"
        }`
      }
    >
      <Icon size={18} aria-hidden="true" />
      {item.label}
    </NavLink>
  );
}

/** Slide-in navigation for phones (< md). Desktop uses the fixed sidebar. */
export function MobileDrawer({ open, onClose }: MobileDrawerProps) {
  // Close on Escape; lock body scroll while open.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 md:hidden" role="dialog" aria-modal="true" aria-label="Navigation">
      <button
        type="button"
        aria-label="Close navigation"
        onClick={onClose}
        className="absolute inset-0 bg-navy-950/60 backdrop-blur-sm animate-fade-in"
      />
      <div className="animate-rise-in absolute left-0 top-0 flex h-full w-72 max-w-[80vw] flex-col bg-navy-900 shadow-2xl">
        <div className="flex items-center justify-between px-4 pb-4 pt-5">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-600">
              <ShieldCheck size={20} className="text-white" aria-hidden="true" />
            </div>
            <p className="text-base font-bold tracking-wide text-white">ID-SHIELD</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close menu"
            className="rounded-lg p-2 text-navy-300 hover:bg-navy-800 hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-500"
          >
            <X size={20} aria-hidden="true" />
          </button>
        </div>

        <nav aria-label="Mobile" className="flex-1 space-y-1 overflow-y-auto px-3 pb-4">
          {NAV_MAIN.map((item) => (
            <DrawerLink key={item.to} item={item} onClose={onClose} />
          ))}
          <div className="my-3 border-t border-navy-700/60" />
          {NAV_SECONDARY.map((item) => (
            <DrawerLink key={item.to} item={item} onClose={onClose} />
          ))}
        </nav>

        <div className="border-t border-navy-700/60 p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-navy-600 text-xs font-bold text-navy-100">
              AV
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-white">A. Verifier</p>
              <p className="text-[11px] text-navy-300">Verification Officer</p>
            </div>
            <span title="Log out (disabled in prototype)" className="text-navy-400">
              <LogOut size={16} aria-hidden="true" />
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
