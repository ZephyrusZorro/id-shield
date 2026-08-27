"""Image loading + non-destructive preprocessing.

Originals are never modified; processed derivatives are stored separately.
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

MAX_SIDE = 2000
_SKEW_LIMIT_DEG = 15.0


def load_image(path: Path) -> np.ndarray:
    """Load an image or render a PDF's first page to BGR ndarray."""
    if path.suffix.lower() == ".pdf":
        return _load_pdf(path)
    data = np.fromfile(str(path), dtype=np.uint8)  # unicode-safe on Windows
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Unable to decode image file: {path.name}")
    return image


def _load_pdf(path: Path) -> np.ndarray:
    import fitz  # PyMuPDF

    with fitz.open(path) as pdf:
        page = pdf.load_page(0)
        pix = page.get_pixmap(dpi=200)
        arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
            pix.height, pix.width, pix.n
        )
        if pix.n == 4:
            return cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
        return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)


def estimate_skew(gray: np.ndarray) -> float:
    """Estimate skew via projection-profile sharpness over small angles.

    minAreaRect over all ink pixels is unreliable for sparse letter-style
    layouts; scanning candidate angles and scoring row-histogram contrast is
    robust for typical photo skews (±3 degrees).
    """
    mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    if cv2.countNonZero(mask) < 200:  # effectively blank
        return 0.0
    h, w = mask.shape
    best_angle, best_score = 0.0, -1.0
    for angle in np.arange(-3.0, 3.01, 0.25):
        matrix = cv2.getRotationMatrix2D((w / 2, h / 2), float(angle), 1.0)
        rotated = cv2.warpAffine(
            mask, matrix, (w, h), flags=cv2.INTER_NEAREST, borderValue=0
        )
        profile = rotated.sum(axis=1, dtype=np.int64)
        score = float(np.square(np.diff(profile)).sum())
        if score > best_score:
            best_score = score
            best_angle = float(angle)
    return round(best_angle, 2)


def preprocess(image_bgr: np.ndarray, out_path: Path) -> dict:
    """Produce an OCR-friendly derivative. Returns processing metadata."""
    steps: list[str] = []
    h, w = image_bgr.shape[:2]

    longest = max(h, w)
    if longest > MAX_SIDE:
        scale = MAX_SIDE / longest
        image_bgr = cv2.resize(image_bgr, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
        steps.append(f"resized {w}x{h}->{image_bgr.shape[1]}x{image_bgr.shape[0]}")

    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)

    skew = estimate_skew(gray)
    if abs(skew) >= 0.5 and abs(skew) <= _SKEW_LIMIT_DEG:
        center = (gray.shape[1] // 2, gray.shape[0] // 2)
        matrix = cv2.getRotationMatrix2D(center, skew, 1.0)
        gray = cv2.warpAffine(
            gray, matrix, (gray.shape[1], gray.shape[0]),
            flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE,
        )
        steps.append(f"deskewed {skew}deg")

    # Note: aggressive enhancement (CLAHE / denoise) is deliberately omitted —
    # Tesseract performs its own binarization and heavy filters measurably
    # degrade recognition on high-contrast documents.

    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imencode(".png", gray)[1].tofile(str(out_path))

    return {
        "processed_path": str(out_path),
        "steps": steps,
        "width": int(gray.shape[1]),
        "height": int(gray.shape[0]),
    }
