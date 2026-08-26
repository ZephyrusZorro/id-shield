import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  CloudUpload,
  FileText,
  Loader2,
  Trash2,
  CheckCircle2,
  AlertCircle,
  Sparkles,
} from "lucide-react";
import { PageHeader } from "../components/layout/PageHeader";
import { apiPost, apiPostForm } from "../services/api";
import type { CaseCreated, UploadResult } from "../types/api";

const ACCEPTED = ".jpg,.jpeg,.png,.pdf";
const MAX_MB = 10;
const MAX_BYTES = MAX_MB * 1024 * 1024;

const DOC_CATEGORIES = [
  "Passport",
  "National ID",
  "PAN-like Document",
  "Driving Licence",
  "Address Proof",
  "Visa",
  "Certificate",
  "Other Identity Document",
];

interface PendingFile {
  key: string;
  file: File;
  previewUrl: string | null;
}

function formatSize(bytes: number): string {
  if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

export function NewCasePage() {
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const [caseName, setCaseName] = useState("");
  const [files, setFiles] = useState<PendingFile[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const counter = useRef(0);
  const filesRef = useRef<PendingFile[]>([]);
  filesRef.current = files;

  const addFiles = useCallback(
    (incoming: FileList | File[]) => {
      setError(null);
      const next: PendingFile[] = [];
      const problems: string[] = [];
      for (const f of Array.from(incoming)) {
        const ext = f.name.split(".").pop()?.toLowerCase() ?? "";
        if (!["jpg", "jpeg", "png", "pdf"].includes(ext)) {
          problems.push(`"${f.name}" — unsupported type (.${ext || "?"}). Allowed: JPG, PNG, PDF.`);
          continue;
        }
        if (f.size > MAX_BYTES) {
          problems.push(`"${f.name}" — exceeds the ${MAX_MB} MB limit (${formatSize(f.size)}).`);
          continue;
        }
        if (f.size === 0) {
          problems.push(`"${f.name}" — file is empty.`);
          continue;
        }
        next.push({
          key: `f${counter.current++}`,
          file: f,
          previewUrl: f.type.startsWith("image/") ? URL.createObjectURL(f) : null,
        });
      }
      setFiles((prev) => [...prev, ...next]);
      if (problems.length > 0) setError(problems.join(" "));
    },
    [],
  );

  const removeFile = (key: string) => {
    setFiles((prev) => {
      const target = prev.find((p) => p.key === key);
      if (target?.previewUrl) URL.revokeObjectURL(target.previewUrl);
      return prev.filter((p) => p.key !== key);
    });
  };

  // Revoke any remaining preview URLs if the user leaves mid-flow.
  useEffect(() => {
    return () => {
      filesRef.current.forEach((f) => f.previewUrl && URL.revokeObjectURL(f.previewUrl));
    };
  }, []);

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files?.length) addFiles(e.dataTransfer.files);
  };

  const canSubmit = caseName.trim().length > 0 && files.length > 0 && !submitting;

  const startScreening = async () => {
    if (!canSubmit) return;
    setSubmitting(true);
    setError(null);
    try {
      const created = await apiPost<CaseCreated>("/api/cases", {
        case_name: caseName.trim(),
      });
      const form = new FormData();
      files.forEach((f) => form.append("files", f.file));
      const result = await apiPostForm<UploadResult>(
        `/api/cases/${created.id}/documents`,
        form,
      );
      files.forEach((f) => f.previewUrl && URL.revokeObjectURL(f.previewUrl));
      if (result.failed.length > 0) {
        setError(
          result.failed.map((f) => `"${f.file_name}" — ${f.error}`).join(" "),
        );
        if (result.uploaded.length === 0) {
          setSubmitting(false);
          return;
        }
      }
      await apiPost(`/api/cases/${created.id}/analyze`);
      navigate(`/screen/processing/${created.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
      setSubmitting(false);
    }
  };

  const loadDemoCase = async () => {
    setSubmitting(true);
    setError(null);
    try {
      const created = await apiPost<CaseCreated>("/api/demo/signature-case");
      navigate(`/screen/processing/${created.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load the demo case.");
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto max-w-4xl animate-fade-in">
      <PageHeader
        title="New Case"
        subtitle="Upload identity documents for screening"
        actions={
          <button
            type="button"
            onClick={loadDemoCase}
            disabled={submitting}
            className="btn-secondary"
            title="Loads a prepared synthetic case (Rahul Sharma) through the full pipeline"
          >
            {submitting ? (
              <Loader2 size={16} className="animate-spin" aria-hidden="true" />
            ) : (
              <Sparkles size={16} className="text-blue-500" aria-hidden="true" />
            )}
            Load Demo Case
          </button>
        }
      />

      <div className="card p-6">
        {/* Case name */}
        <label htmlFor="case-name" className="mb-1.5 block text-sm font-semibold text-navy-900">
          Case Name <span className="text-red-500">*</span>
        </label>
        <input
          id="case-name"
          type="text"
          className="input-field"
          placeholder="e.g. Onboarding verification — R. Sharma"
          value={caseName}
          maxLength={200}
          onChange={(e) => setCaseName(e.target.value)}
        />

        {/* Dropzone */}
        <div className="mt-6">
          <p className="mb-1.5 text-sm font-semibold text-navy-900">
            Documents <span className="text-red-500">*</span>
          </p>
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            onKeyDown={(e) => e.key === "Enter" && inputRef.current?.click()}
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={onDrop}
            aria-label="Add identity documents"
            className={`flex w-full flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-12 text-center transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 ${
              dragOver
                ? "border-blue-500 bg-blue-50/70"
                : "border-slate-300 bg-slate-50/60 hover:border-blue-400 hover:bg-blue-50/40"
            }`}
          >
            <CloudUpload size={36} className="text-slate-400" aria-hidden="true" />
            <span className="mt-3 text-sm font-semibold text-navy-900">
              Drag &amp; drop documents here, or click to browse
            </span>
            <span className="mt-1 text-xs text-slate-400">
              JPG · JPEG · PNG · PDF — max {MAX_MB} MB per file — multiple files supported
            </span>
            <span className="mt-3 text-xs font-medium text-blue-600">
              All documents are treated as untrusted input and stored locally.
            </span>
          </button>
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPTED}
            multiple
            hidden
            onChange={(e) => {
              if (e.target.files?.length) addFiles(e.target.files);
              e.target.value = "";
            }}
          />
        </div>

        {/* File list */}
        {files.length > 0 && (
          <ul className="mt-5 space-y-2.5" aria-label="Selected documents">
            {files.map(({ key, file, previewUrl }) => (
              <li
                key={key}
                className="animate-rise-in flex items-center gap-3 rounded-lg border border-slate-200 bg-white p-2.5 shadow-card"
              >
                {previewUrl ? (
                  <img
                    src={previewUrl}
                    alt={`Preview of ${file.name}`}
                    className="h-12 w-16 shrink-0 rounded-md border border-slate-200 object-cover"
                  />
                ) : (
                  <div className="flex h-12 w-16 shrink-0 items-center justify-center rounded-md bg-navy-50">
                    <FileText size={20} className="text-navy-500" aria-hidden="true" />
                  </div>
                )}
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-semibold text-navy-900">{file.name}</p>
                  <p className="text-xs text-slate-400">
                    {formatSize(file.size)} · ready for upload
                  </p>
                </div>
                <CheckCircle2 size={17} className="shrink-0 text-emerald-500" aria-hidden="true" />
                <button
                  type="button"
                  onClick={() => removeFile(key)}
                  aria-label={`Remove ${file.name}`}
                  className="rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-red-50 hover:text-red-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-red-500"
                >
                  <Trash2 size={16} aria-hidden="true" />
                </button>
              </li>
            ))}
          </ul>
        )}

        {/* Errors */}
        {error && (
          <div role="alert" className="mt-4 flex items-start gap-2.5 rounded-lg bg-red-50 px-4 py-3">
            <AlertCircle size={16} className="mt-0.5 shrink-0 text-red-500" aria-hidden="true" />
            <p className="text-xs leading-relaxed text-red-700">{error}</p>
          </div>
        )}

        {/* Categories + CTA */}
        <div className="mt-6 flex flex-wrap gap-2" aria-label="Supported document categories">
          {DOC_CATEGORIES.map((c) => (
            <span
              key={c}
              className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-500"
            >
              {c}
            </span>
          ))}
        </div>

        <div className="mt-6 flex justify-end border-t border-slate-100 pt-5">
          <button type="button" onClick={startScreening} disabled={!canSubmit} className="btn-primary">
            {submitting ? (
              <>
                <Loader2 size={16} className="animate-spin" aria-hidden="true" />
                Uploading…
              </>
            ) : (
              "Start Screening / Analyze"
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
