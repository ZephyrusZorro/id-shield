import { useState } from "react";
import { FileWarning } from "lucide-react";

interface DocImageProps {
  src: string;
  alt: string;
  className?: string;
  /** Extra classes for the fallback box (e.g. aspect ratio). */
  fallbackClassName?: string;
  onLoad?: (e: React.SyntheticEvent<HTMLImageElement>) => void;
}

/**
 * Document preview that degrades gracefully when the stored file is
 * missing or undecodable — never a broken-image glyph.
 */
export function DocImage({ src, alt, className, fallbackClassName, onLoad }: DocImageProps) {
  // Track which src failed so switching documents resets the fallback.
  const [failedSrc, setFailedSrc] = useState<string | null>(null);
  const failed = failedSrc === src;

  if (failed) {
    return (
      <div
        role="img"
        aria-label={`${alt} (preview unavailable)`}
        className={`flex items-center justify-center rounded-lg border border-slate-200 bg-slate-50 ${fallbackClassName ?? ""}`}
      >
        <div className="p-3 text-center">
          <FileWarning size={22} className="mx-auto text-slate-300" aria-hidden="true" />
          <p className="mt-1 text-[10px] font-medium uppercase tracking-wide text-slate-400">
            Preview unavailable
          </p>
        </div>
      </div>
    );
  }

  return (
    <img
      src={src}
      alt={alt}
      loading="lazy"
      onError={() => setFailedSrc(src)}
      onLoad={onLoad}
      className={className}
    />
  );
}
