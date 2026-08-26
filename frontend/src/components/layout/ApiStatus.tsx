import { useEffect, useState } from "react";
import { API_BASE } from "../../services/api";

/**
 * Backend connectivity indicator shown in the top bar.
 * Polls the health endpoint; communicates state via text + color.
 */
export function ApiStatus() {
  const [online, setOnline] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    const check = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/health`);
        if (!cancelled) setOnline(res.ok);
      } catch {
        if (!cancelled) setOnline(false);
      }
    };
    void check();
    const id = setInterval(check, 15000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  if (online === null) return null;

  return (
    <div
      className="flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1.5"
      role="status"
      aria-label={online ? "Backend connected" : "Backend offline"}
    >
      <span className="relative flex h-2 w-2">
        <span
          className={`absolute inline-flex h-full w-full rounded-full opacity-60 ${
            online ? "animate-ping bg-emerald-400" : ""
          }`}
        />
        <span
          className={`relative inline-flex h-2 w-2 rounded-full ${
            online ? "bg-emerald-500" : "bg-red-500"
          }`}
        />
      </span>
      <span className="text-xs font-medium text-slate-600">
        {online ? "API Connected" : "API Offline"}
      </span>
    </div>
  );
}
