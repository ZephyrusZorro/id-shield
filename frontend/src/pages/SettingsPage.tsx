import {
  Sliders,
  Shield,
  Server,
  Cpu,
  CheckCircle,
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
        subtitle="Forensics engine parameters, module toggles, and security configurations"
      />

      {/* System Status Banner */}
      <div className="rounded-xl border border-blue-100 bg-blue-50/50 p-5 shadow-sm">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-600 text-white shadow-sm">
              <Server className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-navy-900">{health?.app || "ID-SHIELD Platform"}</h3>
                <span className="rounded bg-emerald-100 px-2 py-0.5 text-[10px] font-bold text-emerald-800">
                  {loading ? "Checking..." : "Operational"}
                </span>
              </div>
              <p className="text-xs text-slate-500">
                v{health?.version || "0.1.0"} · {health?.tagline || "Explainable Identity & Document Forensics"}
              </p>
            </div>
          </div>
          <div className="text-xs text-slate-500 sm:text-right">
            <div>Deployment Mode: <span className="font-semibold text-navy-900">Unified Container / Production</span></div>
            <div>Engine Status: <span className="font-semibold text-emerald-600">All 10 Modules Online</span></div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        {/* Forensics & Verification Pipeline Modules */}
        <div className="card p-5 space-y-4">
          <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
            <Cpu className="h-4 w-4 text-blue-600" />
            <h3 className="font-bold text-sm text-navy-900">Verification Pipeline Modules</h3>
          </div>

          <div className="space-y-3 text-xs">
            {[
              { name: "Image Preprocessing & Deskew", status: "Active", desc: "Automated skew angle correction & contrast normalization" },
              { name: "Multi-Pass OCR Engine", status: "Active", desc: "Tesseract OCR with word confidence scoring" },
              { name: "ICAO TD3 MRZ Checksums", status: "Active", desc: "7-3-5 weighting algorithm and printed text cross-check" },
              { name: "Visual Forensics (ELA & Noise)", status: "Active", desc: "Pixel tampering localization and artifact detection" },
              { name: "Cross-Document Consistency", status: "Active", desc: "Multi-field fuzzy name, date, and address comparison" },
              { name: "Facial Match & Biometrics", status: "Enabled", desc: "Facial photo extraction and perceptual distance scoring" },
              { name: "Exact Document Reuse Detection", status: "Active", desc: "Cross-case SHA-256 exact match scanning" },
            ].map((mod) => (
              <div key={mod.name} className="flex items-start justify-between rounded-lg border border-slate-100 bg-slate-50/50 p-2.5">
                <div>
                  <div className="font-semibold text-navy-900">{mod.name}</div>
                  <div className="text-[11px] text-slate-500">{mod.desc}</div>
                </div>
                <span className="inline-flex items-center gap-1 rounded bg-emerald-50 px-2 py-0.5 text-[10px] font-bold text-emerald-700">
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
            <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
              <Shield className="h-4 w-4 text-blue-600" />
              <h3 className="font-bold text-sm text-navy-900">Security & Upload Policies</h3>
            </div>

            <div className="space-y-3 text-xs">
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span className="text-slate-500">Allowed File Types</span>
                <span className="font-mono font-semibold text-navy-900">JPG, JPEG, PNG, PDF</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span className="text-slate-500">Max Upload Size</span>
                <span className="font-mono font-semibold text-navy-900">10 MB per file</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span className="text-slate-500">Header Magic Byte Sniffing</span>
                <span className="font-semibold text-emerald-600">Enforced (Binary Signatures)</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span className="text-slate-500">Storage Encryption & Isolation</span>
                <span className="font-semibold text-navy-900">Case UUID Directory Sandboxing</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-slate-500">Security Headers</span>
                <span className="font-semibold text-navy-900">CSP, XFO, XCTO, Permissions-Policy</span>
              </div>
            </div>
          </div>

          <div className="card p-5 space-y-4">
            <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
              <Sliders className="h-4 w-4 text-blue-600" />
              <h3 className="font-bold text-sm text-navy-900">Risk Fusion Weights</h3>
            </div>

            <div className="space-y-2.5 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-slate-600">Cross-Document Date of Birth Mismatch</span>
                <span className="rounded bg-rose-100 px-2 py-0.5 font-mono font-bold text-rose-700">+35 pts</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-600">Visual Forensics Tampering Detected</span>
                <span className="rounded bg-rose-100 px-2 py-0.5 font-mono font-bold text-rose-700">+30 pts</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-600">MRZ / QR Checksum Failure</span>
                <span className="rounded bg-amber-100 px-2 py-0.5 font-mono font-bold text-amber-700">+25 pts</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-600">Cross-Document Full Name Conflict</span>
                <span className="rounded bg-amber-100 px-2 py-0.5 font-mono font-bold text-amber-700">+20 pts</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-600">Multi-Document Agreement Bonus</span>
                <span className="rounded bg-emerald-100 px-2 py-0.5 font-mono font-bold text-emerald-700">-15 pts</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
