"""Face extraction & cross-matching forensics service.

Detects facial photos in identity documents, evaluates image quality
(sharpness, contrast, illumination), extracts multi-modal biometric/visual
features, and computes an explainable multi-metric similarity score across
submitted documents in a case.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

import cv2
import imagehash
import numpy as np
from PIL import Image

from app.core.config import settings
from app.core.logging import get_logger
from app.services.forensic_service import REGION_MAPS

log = get_logger("idshield.faces")

# Standardized face crop dimensions for consistent feature extraction
FACE_CROP_SIZE = (160, 160)

# Similarity thresholds
MATCH_THRESHOLD = 70.0       # >= 70% is considered a confident match
BORDERLINE_THRESHOLD = 50.0  # 50% - 69% requires review; < 50% is a mismatch


@dataclass
class FaceCropResult:
    """Detected face metadata and features for a single document."""
    document_id: str
    file_name: str
    bbox: list[int]  # [x, y, w, h] in image pixel coordinates
    normalized_bbox: list[float]  # [x, y, w, h] normalized 0..1
    confidence: float  # 0..1 detection confidence
    detection_method: str  # "cascade" | "layout_photo_zone"
    sharpness: float  # Laplacian variance
    brightness: float  # Mean pixel intensity 0..255
    contrast: float  # Pixel std deviation
    crop_path: str | None = None  # Relative path to saved face crop PNG
    features: dict = field(default_factory=dict)


@dataclass
class FaceComparisonResult:
    """Pairwise comparison between two document face photos."""
    doc_a_id: str
    doc_a_name: str
    doc_b_id: str
    doc_b_name: str
    similarity_score: int  # 0..100
    status: str  # "match" | "borderline" | "mismatch"
    severity: str  # "info" | "medium" | "high"
    explanation: str
    ssim_score: float  # 0..1
    phash_similarity: float  # 0..1
    lbp_correlation: float  # 0..1
    color_correlation: float  # 0..1


def _get_face_cascade() -> cv2.CascadeClassifier | None:
    """Load OpenCV pre-trained Haar Cascades."""
    try:
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        cascade = cv2.CascadeClassifier(cascade_path)
        if not cascade.empty():
            return cascade
    except Exception as exc:
        log.warning("CASCADE_LOAD_ERROR | err=%s", exc)
    return None


def _get_alt_cascade() -> cv2.CascadeClassifier | None:
    """Load alternative Haar Cascade for profile or low-angle faces."""
    try:
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_alt2.xml"
        cascade = cv2.CascadeClassifier(cascade_path)
        if not cascade.empty():
            return cascade
    except Exception:
        pass
    return None


def _compute_lbp(gray: np.ndarray) -> np.ndarray:
    """Calculate Local Binary Patterns (LBP) texture descriptor."""
    h, w = gray.shape
    lbp = np.zeros((h - 2, w - 2), dtype=np.uint8)
    center = gray[1 : h - 1, 1 : w - 1]
    
    # 8 neighbors comparison
    offsets = [
        (-1, -1), (-1, 0), (-1, 1),
        (0, 1), (1, 1), (1, 0),
        (1, -1), (0, -1)
    ]
    for i, (dy, dx) in enumerate(offsets):
        neighbor = gray[1 + dy : h - 1 + dy, 1 + dx : w - 1 + dx]
        lbp |= ((neighbor >= center).astype(np.uint8) << i)
        
    hist, _ = np.histogram(lbp.ravel(), bins=256, range=(0, 256))
    hist = hist.astype(np.float32)
    hist /= (hist.sum() + 1e-7)
    return hist


def _compute_ssim(img1: np.ndarray, img2: np.ndarray) -> float:
    """Calculate Structural Similarity Index (SSIM) between two grayscale images."""
    if img1.shape != img2.shape:
        img2 = cv2.resize(img2, (img1.shape[1], img1.shape[0]))

    c1 = (0.01 * 255) ** 2
    c2 = (0.03 * 255) ** 2

    img1 = img1.astype(np.float64)
    img2 = img2.astype(np.float64)

    mu1 = cv2.GaussianBlur(img1, (11, 11), 1.5)
    mu2 = cv2.GaussianBlur(img2, (11, 11), 1.5)

    mu1_sq = mu1 ** 2
    mu2_sq = mu2 ** 2
    mu1_mu2 = mu1 * mu2

    sigma1_sq = cv2.GaussianBlur(img1 ** 2, (11, 11), 1.5) - mu1_sq
    sigma2_sq = cv2.GaussianBlur(img2 ** 2, (11, 11), 1.5) - mu2_sq
    sigma12 = cv2.GaussianBlur(img1 * img2, (11, 11), 1.5) - mu1_mu2

    ssim_map = ((2 * mu1_mu2 + c1) * (2 * sigma12 + c2)) / (
        (mu1_sq + mu2_sq + c1) * (sigma1_sq + sigma2_sq + c2)
    )
    return float(np.clip(ssim_map.mean(), 0.0, 1.0))


def extract_face(
    image: np.ndarray,
    doc_id: str,
    file_name: str,
    doc_type: str | None = None,
    save_crop_dir: Path | None = None,
) -> FaceCropResult | None:
    """Detect and extract the primary face from a document image."""
    h, w = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

    # 1. Try Cascade detection
    cascade = _get_face_cascade()
    faces = []
    if cascade is not None:
        faces = cascade.detectMultiScale(
            gray,
            scaleFactor=1.08,
            minNeighbors=4,
            minSize=(int(w * 0.08), int(h * 0.08)),
        )

    # 2. Try Alt Cascade if default found nothing
    if len(faces) == 0:
        alt_cascade = _get_alt_cascade()
        if alt_cascade is not None:
            faces = alt_cascade.detectMultiScale(
                gray,
                scaleFactor=1.05,
                minNeighbors=3,
                minSize=(int(w * 0.08), int(h * 0.08)),
            )

    detection_method = "cascade"
    best_box = None

    if len(faces) > 0:
        # Choose the largest detected face box
        best_box = max(faces, key=lambda b: b[2] * b[3])
        x, y, fw, fh = int(best_box[0]), int(best_box[1]), int(best_box[2]), int(best_box[3])
        confidence = 0.90
    else:
        # 3. Fallback to document layout photo zone if known
        dtype = (doc_type or "").lower()
        zone_map = REGION_MAPS.get(dtype)
        if zone_map and "photo zone" in zone_map:
            x0_f, y0_f, x1_f, y1_f = zone_map["photo zone"]
            x = int(x0_f * w)
            y = int(y0_f * h)
            fw = int((x1_f - x0_f) * w)
            fh = int((y1_f - y0_f) * h)
            detection_method = "layout_photo_zone"
            confidence = 0.65
        else:
            return None

    # Clamp bounding box
    x = max(0, min(x, w - 1))
    y = max(0, min(y, h - 1))
    fw = max(10, min(fw, w - x))
    fh = max(10, min(fh, h - y))

    face_crop = image[y : y + fh, x : x + fw]
    if face_crop.size == 0:
        return None

    # Quality metrics
    crop_gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY) if len(face_crop.shape) == 3 else face_crop
    sharpness = float(cv2.Laplacian(crop_gray, cv2.CV_64F).var())
    brightness = float(np.mean(crop_gray))
    contrast = float(np.std(crop_gray))

    # Standardize crop for comparison
    aligned_crop = cv2.resize(face_crop, FACE_CROP_SIZE)
    aligned_gray = cv2.resize(crop_gray, FACE_CROP_SIZE)
    aligned_gray_eq = cv2.equalizeHist(aligned_gray)

    # Compute feature representations
    pil_crop = Image.fromarray(cv2.cvtColor(aligned_crop, cv2.COLOR_BGR2RGB))
    phash_val = str(imagehash.phash(pil_crop))
    dhash_val = str(imagehash.dhash(pil_crop))

    # LBP texture histogram
    lbp_hist = _compute_lbp(aligned_gray_eq).tolist()

    # Color HSV histogram
    hsv = cv2.cvtColor(aligned_crop, cv2.COLOR_BGR2HSV)
    color_hist = cv2.calcHist([hsv], [0, 1], None, [16, 16], [0, 180, 0, 256])
    cv2.normalize(color_hist, color_hist, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
    color_hist_list = color_hist.flatten().tolist()

    crop_rel_path = None
    if save_crop_dir is not None:
        save_crop_dir.mkdir(parents=True, exist_ok=True)
        crop_file = save_crop_dir / f"{doc_id}_face.png"
        cv2.imwrite(str(crop_file), face_crop)
        try:
            crop_rel_path = str(crop_file.relative_to(settings.upload_dir))
        except ValueError:
            crop_rel_path = str(crop_file)

    return FaceCropResult(
        document_id=doc_id,
        file_name=file_name,
        bbox=[x, y, fw, fh],
        normalized_bbox=[round(x / w, 4), round(y / h, 4), round(fw / w, 4), round(fh / h, 4)],
        confidence=confidence,
        detection_method=detection_method,
        sharpness=round(sharpness, 2),
        brightness=round(brightness, 2),
        contrast=round(contrast, 2),
        crop_path=crop_rel_path,
        features={
            "phash": phash_val,
            "dhash": dhash_val,
            "lbp_hist": lbp_hist,
            "color_hist": color_hist_list,
        },
    )


def compare_two_faces(
    face_a: FaceCropResult,
    face_b: FaceCropResult,
    image_a_path: Path,
    image_b_path: Path,
) -> FaceComparisonResult:
    """Compare two detected face crops and compute explainable similarity."""
    # 1. Load and align crops
    x_a, y_a, w_a, h_a = face_a.bbox
    x_b, y_b, w_b, h_b = face_b.bbox

    img_a = cv2.imread(str(image_a_path))
    img_b = cv2.imread(str(image_b_path))

    if img_a is None or img_b is None:
        return FaceComparisonResult(
            doc_a_id=face_a.document_id,
            doc_a_name=face_a.file_name,
            doc_b_id=face_b.document_id,
            doc_b_name=face_b.file_name,
            similarity_score=50,
            status="borderline",
            severity="medium",
            explanation="Could not load document images for biometric comparison.",
            ssim_score=0.5,
            phash_similarity=0.5,
            lbp_correlation=0.5,
            color_correlation=0.5,
        )

    crop_a = cv2.resize(img_a[y_a : y_a + h_a, x_a : x_a + w_a], FACE_CROP_SIZE)
    crop_b = cv2.resize(img_b[y_b : y_b + h_b, x_b : x_b + w_b], FACE_CROP_SIZE)

    gray_a = cv2.equalizeHist(cv2.cvtColor(crop_a, cv2.COLOR_BGR2GRAY))
    gray_b = cv2.equalizeHist(cv2.cvtColor(crop_b, cv2.COLOR_BGR2GRAY))

    # Metric 1: Structural Similarity (SSIM)
    ssim = _compute_ssim(gray_a, gray_b)

    # Metric 2: Perceptual Hash distance
    try:
        phash_a = imagehash.hex_to_hash(face_a.features.get("phash", "0000000000000000"))
        phash_b = imagehash.hex_to_hash(face_b.features.get("phash", "0000000000000000"))
        phash_dist = phash_a - phash_b
        # Max phash distance is 64 bits
        phash_sim = max(0.0, 1.0 - (phash_dist / 32.0))
    except Exception:
        phash_sim = 0.5

    # Metric 3: LBP Texture correlation
    try:
        lbp_a = np.array(face_a.features["lbp_hist"], dtype=np.float32)
        lbp_b = np.array(face_b.features["lbp_hist"], dtype=np.float32)
        lbp_corr = float(cv2.compareHist(lbp_a, lbp_b, cv2.HISTCMP_CORREL))
        lbp_corr = max(0.0, min(1.0, (lbp_corr + 1.0) / 2.0))  # Scale from [-1, 1] to [0, 1]
    except Exception:
        lbp_corr = 0.5

    # Metric 4: Color / Chroma histogram correlation
    try:
        col_a = np.array(face_a.features["color_hist"], dtype=np.float32)
        col_b = np.array(face_b.features["color_hist"], dtype=np.float32)
        col_corr = float(cv2.compareHist(col_a, col_b, cv2.HISTCMP_CORREL))
        col_corr = max(0.0, min(1.0, (col_corr + 1.0) / 2.0))
    except Exception:
        col_corr = 0.5

    # Weighted composite score
    fused = (
        0.35 * ssim
        + 0.25 * phash_sim
        + 0.25 * lbp_corr
        + 0.15 * col_corr
    )
    score = int(round(fused * 100))
    score = max(0, min(100, score))

    if score >= MATCH_THRESHOLD:
        status = "match"
        severity = "info"
        explanation = (
            f"Facial photo matches across {face_a.file_name} and {face_b.file_name} "
            f"({score}% similarity). Facial geometry, structure, and micro-texture are consistent."
        )
    elif score >= BORDERLINE_THRESHOLD:
        status = "borderline"
        severity = "medium"
        explanation = (
            f"Facial similarity between {face_a.file_name} and {face_b.file_name} is borderline "
            f"({score}%). Visual differences may be due to lighting, aging, or scan quality; review recommended."
        )
    else:
        status = "mismatch"
        severity = "high"
        explanation = (
            f"Facial photo discrepancy detected between {face_a.file_name} and {face_b.file_name} "
            f"({score}% similarity). Different individuals appear to be pictured across submitted documents."
        )

    return FaceComparisonResult(
        doc_a_id=face_a.document_id,
        doc_a_name=face_a.file_name,
        doc_b_id=face_b.document_id,
        doc_b_name=face_b.file_name,
        similarity_score=score,
        status=status,
        severity=severity,
        explanation=explanation,
        ssim_score=round(ssim, 3),
        phash_similarity=round(phash_sim, 3),
        lbp_correlation=round(lbp_corr, 3),
        color_correlation=round(col_corr, 3),
    )


def compare_document_faces(
    faces: Sequence[FaceCropResult],
    doc_paths: dict[str, Path],
) -> list[FaceComparisonResult]:
    """Perform pairwise facial cross-matching across all detected document faces."""
    results: list[FaceComparisonResult] = []
    if len(faces) < 2:
        return results

    for i in range(len(faces)):
        for j in range(i + 1, len(faces)):
            face_a = faces[i]
            face_b = faces[j]
            path_a = doc_paths.get(face_a.document_id)
            path_b = doc_paths.get(face_b.document_id)
            if path_a and path_b:
                cmp = compare_two_faces(face_a, face_b, path_a, path_b)
                results.append(cmp)

    return results
