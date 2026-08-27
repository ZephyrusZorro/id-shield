import {
  Sliders,
  Shield,
  Server,
  Cpu,
  CheckCircle,
  Activity,
} from "lucide-react";
import { PageHeader } from "../components/layout/PageHeader";
import { useApi } from "../hooks/useApi";
import type { HealthResponse } from "../types/api";

export function SettingsPage() {
  const { data: health, loading } = useApi<HealthResponse>("/api/health");

  return (
    <div className="mx-auto max-w-6xl animate-fade-in space-y-6 pb-12">
      <PageHeader
        title="Platform Settings & Diagnostics"
        subtitle="Forensics engine parameters, module telemetry, and security policy calibration"
      />

      {/* System Status Banner */}
      <div className="card border-blue-200/60 dark:border-blue-900/40 bg-gradient-to-r from-blue-50/70 via-indigo-50/50 to-slate-50/50 dark:from-blue-950/40 dark:via-indigo-950/20 dark:to-slate-900/40 p-5 shadow-sm">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3.5">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-600 dark:bg-blue-500 text-white shadow-glow-blue">
              <Server className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-navy-900 dark:text-white">{health?.app || "ID-SHIELD Platform"}</h3>
                <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 dark:bg-emerald-950/80 px-2 py-0.5 text-[10px] font-bold text-emerald-800 dark:text-emerald-400">
                  <Activity className="h-3 w-3 animate-pulse" />
                  {loading ? "Checking..." : "Operational"}
                </span>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                v{health?.version || "0.1.0"} · {health?.tagline || "Explainable Identity & Document Forensics Engine"}
              </p>
            </div>
          </div>
          <div className="text-xs text-slate-500 dark:text-slate-400 sm:text-right space-y-0.5">
            <div>Deployment: <span className="font-semibold text-navy-900 dark:text-slate-200">Unified Container / Production</span></div>
            <div>Engine Status: <span className="font-semibold text-emerald-600 dark:text-emerald-400">All 11 Modules Active</span></div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        {/* Forensics & Verification Pipeline Modules */}
        <div className="card p-5 space-y-4">
          <div className="flex items-center gap-2 border-b border-slate-100 dark:border-slate-800/80 pb-3">
            <Cpu className="h-4 w-4 text-blue-600 dark:text-blue-400" />
            <h3 className="font-bold text-sm text-navy-900 dark:text-white">Verification Pipeline Modules</h3>
          </div>

          <div className="space-y-2.5 text-xs">
            {[
              { name: "Image Preprocessing & Deskew", status: "Active", desc: "Automated skew angle correction & contrast normalization" },
              { name: "Multi-Pass OCR Engine", status: "Active", desc: "Tesseract OCR with word confidence scoring and next-line lookahead" },
              { name: "ICAO TD3 MRZ Checksums", status: "Active", desc: "7-3-5 weighting algorithm and printed text cross-check" },
              { name: "Visual Forensics (ELA & Noise)", status: "Active", desc: "Pixel tampering localization and artifact detection" },
              { name: "Cross-Document Consistency", status: "Active", desc: "Multi-field fuzzy name, date, and address comparison" },
              { name: "Facial Match & Biometrics", status: "Active", desc: "Facial photo extraction and perceptual cosine distance scoring" },
              { name: "Document Reuse & Anti-Tampering", status: "Active", desc: "Cross-case SHA-256 and pHash exact match scanning" },
            ].map((mod) => (
              <div key={mod.name} className="flex items-start justify-between rounded-lg border border-slate-100 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-900/40 p-2.5 transition-colors">
                <div>
                  <div className="font-semibold text-navy-900 dark:text-slate-200">{mod.name}</div>
                  <div className="text-[11px] text-slate-500 dark:text-slate-400">{mod.desc}</div>
                </div>
                <span className="inline-flex items-center gap-1 rounded-md bg-emerald-50 dark:bg-emerald-950/60 px-2 py-0.5 text-[10px] font-bold text-emerald-700 dark:text-emerald-400 shrink-0 ml-2">
                  <CheckCircle className="h-3 w-3" />
                  {mod.status}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Security & Storage Configuration */}
        <div className="space-y-6">
          <div className="card p-5 space-y-4">
            <div className="flex items-center gap-2 border-b border-slate-100 dark:border-slate-800/80 pb-3">
              <Shield className="h-4 w-4 text-blue-600 dark:text-blue-400" />
              <h3 className="font-bold text-sm text-navy-900 dark:text-white">Security &amp; Ingestion Safeguards</h3>
            </div>

            <div className="space-y-3 text-xs">
              <div className="flex justify-between py-1.5 border-b border-slate-100 dark:border-slate-800/80">
                <span className="text-slate-500 dark:text-slate-400">Allowed File Ingestion</span>
                <span className="font-mono font-semibold text-navy-900 dark:text-slate-200">JPG, JPEG, PNG, PDF</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-slate-100 dark:border-slate-800/80">
                <span className="text-slate-500 dark:text-slate-400">Max Upload Cap</span>
                <span className="font-mono font-semibold text-navy-900 dark:text-slate-200">10 MB per file</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-slate-100 dark:border-slate-800/80">
                <span className="text-slate-500 dark:text-slate-400">Header Magic Byte Sniffing</span>
                <span className="font-semibold text-emerald-600 dark:text-emerald-400">Enforced (Binary Signatures)</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-slate-100 dark:border-slate-800/80">
                <span className="text-slate-500 dark:text-slate-400">Storage Sandboxing</span>
                <span className="font-semibold text-navy-900 dark:text-slate-200">Case UUID Directory Isolation</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-slate-500 dark:text-slate-400">HTTP Security Headers</span>
                <span className="font-semibold text-navy-900 dark:text-slate-200">CSP, XFO, XCTO, Perm-Policy</span>
              </div>
            </div>
          </div>

          <div className="card p-5 space-y-4">
            <div className="flex items-center gap-2 border-b border-slate-100 dark:border-slate-800/80 pb-3">
              <Sliders className="h-4 w-4 text-blue-600 dark:text-blue-400" />
              <h3 className="font-bold text-sm text-navy-900 dark:text-white">Risk Engine Calibration</h3>
            </div>

            <div className="space-y-2.5 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-slate-600 dark:text-slate-300">Cross-Document Date of Birth Mismatch</span>
                <span className="rounded bg-rose-100 dark:bg-rose-950/80 px-2 py-0.5 font-mono font-bold text-rose-700 dark:text-rose-400">+35 pts</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-600 dark:text-slate-300">Visual Forensics Tampering Detected</span>
                <span className="rounded bg-rose-100 dark:bg-rose-950/80 px-2 py-0.5 font-mono font-bold text-rose-700 dark:text-rose-400">+30 pts</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-600 dark:text-slate-300">MRZ / QR Checksum Failure</span>
                <span className="rounded bg-amber-100 dark:bg-amber-950/80 px-2 py-0.5 font-mono font-bold text-amber-700 dark:text-amber-400">+25 pts</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-600 dark:text-slate-300">Cross-Document Full Name Conflict</span>
                <span className="rounded bg-amber-100 dark:bg-amber-950/80 px-2 py-0.5 font-mono font-bold text-amber-700 dark:text-amber-400">+20 pts</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-600 dark:text-slate-300">Multi-Document Agreement Reduction</span>
                <span className="rounded bg-emerald-100 dark:bg-emerald-950/80 px-2 py-0.5 font-mono font-bold text-emerald-700 dark:text-emerald-400">-15 pts</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
