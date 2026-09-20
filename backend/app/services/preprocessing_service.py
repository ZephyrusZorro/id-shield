"""Image loading + non-destructive preprocessing pipeline for document forensics and OCR.

Original uploaded documents are NEVER modified; processed derivatives are stored
separately in designated output paths.

Supported pipeline stages:
- High-resolution PDF page rendering (PyMuPDF / fitz)
- Resizing (bounded scaling for optimal character recognition)
- Orientation detection & correction (0°, 90°, 180°, 270°)
- Multi-angle projection profile deskewing (±15°)
- Grayscale conversion
- Dynamic range contrast normalization
- Edge-preserving bilateral denoising
- CLAHE (Contrast Limited Adaptive Histogram Equalization)
- Unsharp mask text edge sharpening
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

MIN_OCR_SIDE = 800
MAX_OCR_SIDE = 2000
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


def _load_pdf(path: Path, dpi: int = 200) -> np.ndarray:
    """Render page 0 of a PDF into high-res BGR image via PyMuPDF."""
    import fitz  # PyMuPDF

    with fitz.open(path) as pdf:
        if len(pdf) == 0:
            raise ValueError(f"PDF document is empty: {path.name}")
        page = pdf.load_page(0)
        pix = page.get_pixmap(dpi=dpi)
        arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
            pix.height, pix.width, pix.n
        )
        if pix.n == 4:
            return cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
        return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)


def correct_orientation(image_bgr: np.ndarray) -> tuple[np.ndarray, int]:
    """Detect text orientation (0, 90, 180, 270) via Tesseract OSD if available and rotate."""
    try:
        import pytesseract

        # OSD requires a reasonably sized RGB image
        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        osd = pytesseract.image_to_osd(rgb, output_type=pytesseract.Output.DICT)
        rotate_deg = int(osd.get("rotate", 0))

        if rotate_deg == 90:
            return cv2.rotate(image_bgr, cv2.ROTATE_90_CLOCKWISE), 90
        elif rotate_deg == 180:
            return cv2.rotate(image_bgr, cv2.ROTATE_180), 180
        elif rotate_deg == 270:
            return cv2.rotate(image_bgr, cv2.ROTATE_90_COUNTERCLOCKWISE), 270
    except Exception:
        # Fallback gracefully if OSD is unavailable or text is sparse
        pass
    return image_bgr, 0


def estimate_skew(gray: np.ndarray, max_angle: float = _SKEW_LIMIT_DEG) -> float:
    """Estimate skew via projection-profile sharpness over candidate angles.

    Uses a coarse scan followed by a fine scan for accuracy and performance.
    """
    mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    if cv2.countNonZero(mask) < 200:  # effectively blank
        return 0.0

    h, w = mask.shape
    center = (w / 2, h / 2)

    # Coarse scan from -max_angle to +max_angle in 1.0 deg steps
    coarse_angles = np.arange(-max_angle, max_angle + 0.1, 1.0)
    best_angle, best_score = 0.0, -1.0

    for angle in coarse_angles:
        matrix = cv2.getRotationMatrix2D(center, float(angle), 1.0)
        rotated = cv2.warpAffine(
            mask, matrix, (w, h), flags=cv2.INTER_NEAREST, borderValue=0
        )
        profile = rotated.sum(axis=1, dtype=np.int64)
        score = float(np.square(np.diff(profile)).sum())
        if score > best_score:
            best_score = score
            best_angle = float(angle)

    # Fine scan: refine within ±1.0 degree of best coarse angle in 0.2 deg steps
    fine_angles = np.arange(best_angle - 1.0, best_angle + 1.01, 0.2)
    for angle in fine_angles:
        if abs(angle) > max_angle:
            continue
        matrix = cv2.getRotationMatrix2D(center, float(angle), 1.0)
        rotated = cv2.warpAffine(
            mask, matrix, (w, h), flags=cv2.INTER_NEAREST, borderValue=0
        )
        profile = rotated.sum(axis=1, dtype=np.int64)
        score = float(np.square(np.diff(profile)).sum())
        if score > best_score:
            best_score = score
            best_angle = float(angle)

    return round(best_angle, 2)


def deskew_image(gray: np.ndarray, skew: float) -> np.ndarray:
    """Rotate image by skew angle with replication borders."""
    if abs(skew) < 0.3:
        return gray
    h, w = gray.shape[:2]
    matrix = cv2.getRotationMatrix2D((w // 2, h // 2), skew, 1.0)
    return cv2.warpAffine(
        gray, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
    )


def normalize_image(gray: np.ndarray) -> np.ndarray:
    """Normalize dynamic range by contrast stretching (1st to 99th percentile)."""
    p1, p99 = np.percentile(gray, (1, 99))
    if p99 > p1:
        stretched = np.clip((gray.astype(np.float32) - p1) * (255.0 / (p99 - p1)), 0, 255)
        return stretched.astype(np.uint8)
    return cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)  # type: ignore[return-value]


def denoise_image(gray: np.ndarray) -> np.ndarray:
    """Bilateral filter: smooths background texture/noise while keeping text edges sharp."""
    return cv2.bilateralFilter(gray, d=5, sigmaColor=35, sigmaSpace=35)


def enhance_contrast(gray: np.ndarray, clip_limit: float = 2.0) -> np.ndarray:
    """Adaptive histogram equalization (CLAHE) to balance lighting without blowing highlights."""
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8))
    return clahe.apply(gray)


def sharpen_image(gray: np.ndarray) -> np.ndarray:
    """Unsharp masking to crisp character edges before optical character recognition."""
    blurred = cv2.GaussianBlur(gray, (0, 0), sigmaX=2.0)
    sharpened = cv2.addWeighted(gray, 1.25, blurred, -0.25, 0)
    return np.clip(sharpened, 0, 255).astype(np.uint8)


def resize_image_for_ocr(
    image: np.ndarray, min_side: int = MIN_OCR_SIDE, max_side: int = MAX_OCR_SIDE
) -> tuple[np.ndarray, str | None]:
    """Ensure document dimensions fall into optimal OCR bounds without distortion."""
    h, w = image.shape[:2]
    longest = max(h, w)
    shortest = min(h, w)

    if longest > max_side:
        scale = max_side / longest
        new_w, new_h = int(w * scale), int(h * scale)
        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
        return resized, f"resized {w}x{h}->{new_w}x{new_h}"
    elif shortest < min_side and longest < max_side:
        scale = min(min_side / shortest, max_side / longest)
        if scale > 1.1:
            new_w, new_h = int(w * scale), int(h * scale)
            resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
            return resized, f"resized {w}x{h}->{new_w}x{new_h}"


    return image, None


def preprocess(
    image_bgr: np.ndarray,
    out_path: Path,
    apply_denoise: bool = True,
    apply_clahe: bool = True,
    apply_sharpen: bool = True,
    apply_orientation: bool = True,
) -> dict:
    """Produce an optimized OCR-friendly derivative while keeping the original unchanged.

    Returns comprehensive preprocessing telemetry.
    """
    steps: list[str] = []
    orig_h, orig_w = image_bgr.shape[:2]

    # 1. Orientation detection & correction
    orientation_deg = 0
    if apply_orientation:
        image_bgr, orientation_deg = correct_orientation(image_bgr)
        if orientation_deg != 0:
            steps.append(f"orientation corrected {orientation_deg}deg")

    # 2. Resizing within bounds
    image_bgr, resize_note = resize_image_for_ocr(image_bgr)
    if resize_note:
        steps.append(resize_note)

    # 3. Grayscale conversion
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    steps.append("grayscale conversion")

    # 4. Deskewing
    skew = estimate_skew(gray)
    if abs(skew) >= 0.5 and abs(skew) <= _SKEW_LIMIT_DEG:
        gray = deskew_image(gray, skew)
        steps.append(f"deskewed {skew}deg")

    # 5. Dynamic range normalization
    gray = normalize_image(gray)
    steps.append("dynamic range normalization")

    # 6. Bilateral edge-preserving denoising
    if apply_denoise:
        gray = denoise_image(gray)
        steps.append("bilateral denoising")

    # 7. Adaptive contrast enhancement (CLAHE)
    if apply_clahe:
        gray = enhance_contrast(gray)
        steps.append("contrast enhancement (CLAHE)")

    if apply_sharpen:
        gray = sharpen_image(gray)
        steps.append("text sharpening")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imencode(".png", gray)[1].tofile(str(out_path))

    return {
        "processed_path": str(out_path),
        "steps": steps,
        "width": int(gray.shape[1]),
        "height": int(gray.shape[0]),
        "original_width": orig_w,
        "original_height": orig_h,
        "orientation_deg": orientation_deg,
        "skew_deg": skew,
        "denoised": apply_denoise,
        "contrast_enhanced": apply_clahe,
        "sharpened": apply_sharpen,
    }


def assess_image_quality(image_bgr: np.ndarray) -> dict:
    """Assess document image clarity before OCR/QR/MRZ processing.

    Evaluates:
    - Blur / Sharpness (Laplacian variance)
    - Resolution adequacy
    - Glare / Overexposure / Extreme lighting
    - OCR trust verdict: 'If quality is poor -> don't trust OCR result'
    """
    h, w = image_bgr.shape[:2]
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY) if image_bgr.ndim == 3 else image_bgr

    # 1. Blur / Sharpness via Laplacian variance
    laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    sharpness_status = "good" if laplacian_var >= 100.0 else ("acceptable" if laplacian_var >= 50.0 else "poor")

    # 2. Resolution check
    min_side = min(h, w)
    total_pixels = h * w
    res_status = "good" if (min_side >= 800 and total_pixels >= 600_000) else ("acceptable" if min_side >= 500 else "poor")

    # 3. Glare & Brightness analysis
    mean_brightness = float(np.mean(gray))
    glare_fraction = float(np.mean(gray >= 250))
    dark_fraction = float(np.mean(gray <= 20))
    glare_status = "poor" if (glare_fraction > 0.15 or mean_brightness > 235) else (
        "warning" if (glare_fraction > 0.08 or mean_brightness < 40) else "good"
    )

    # 4. Overall Trust Verdict
    issues = []
    if sharpness_status == "poor":
        issues.append(f"Excessive blur detected (sharpness: {laplacian_var:.1f})")
    elif sharpness_status == "acceptable":
        issues.append(f"Moderate blur (sharpness: {laplacian_var:.1f})")

    if res_status == "poor":
        issues.append(f"Low resolution ({w}x{h} px)")
    if glare_status == "poor":
        issues.append(f"Severe glare/overexposure ({glare_fraction * 100:.1f}% saturated pixels)")

    is_poor = (sharpness_status == "poor" and res_status == "poor") or (sharpness_status == "poor" and glare_status == "poor")
    is_warning = len(issues) > 0 and not is_poor

    status = "fail" if is_poor else ("warning" if is_warning else "pass")
    trust_ocr = not is_poor

    if is_poor:
        verdict_msg = f"Poor image quality: {', '.join(issues)}. Do not trust OCR results without manual verification."
    elif is_warning:
        verdict_msg = f"Acceptable image clarity with minor concerns: {', '.join(issues)}."
    else:
        verdict_msg = f"Excellent image clarity (Sharpness: {laplacian_var:.1f}, Resolution: {w}x{h}, Glare: {glare_fraction * 100:.1f}%). OCR result is trusted."

    return {
        "status": status,
        "trust_ocr": trust_ocr,
        "sharpness": round(laplacian_var, 1),
        "sharpness_status": sharpness_status,
        "resolution": f"{w}x{h}",
        "resolution_status": res_status,
        "glare_percentage": round(glare_fraction * 100, 1),
        "brightness": round(mean_brightness, 1),
        "glare_status": glare_status,
        "message": verdict_msg,
    }

