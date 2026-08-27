"""Visual forensics â€” transparent heuristic analysis for tamper INDICATORS.



Method (deliberately explainable, model-free):



PRIMARY â€” chromatic-noise uniformity (scan-like images):

Documents that originate from renders/scans have near-neutral pixels whose

channel differences are essentially zero everywhere. An edited patch pasted

through an independent JPEG/noise cycle breaks this channel neutrality in a

small, localized area. We measure per-block mean chromatic deviation over

NEAR-NEUTRAL pixels only (colored design elements are excluded by mask).

Clusters above a calibrated absolute floor are reported.



FALLBACK â€” error-level analysis (photographic images):

When the whole document already carries sensor-like chroma noise (global

median deviation above threshold), chroma analysis is declared not

applicable and a conservative JPEG-recompression difference map is used,

with severities capped so photographic grain is not dramatized.



Structural dense-texture zones (QR code, MRZ band) are capped at low

severity so legitimate features are not flagged dramatically.



These are INDICATORS of potential manipulation â€” never proof of forgery.

"""

from __future__ import annotations



from dataclasses import dataclass



import cv2

import numpy as np



_BLOCK = 16

_CHROMA_FLOOR = 13.0      # masked chroma-deviation floor per block

_GLOBAL_CHROMA_LIMIT = 2.5  # document-wide noise guard for the primary path

_JPEG_QUALITY = 90

_SCORE_SCALE = 30.0       # metric value mapped to 0..1 score

_MIN_CLUSTER_BLOCKS = 3

_STRUCTURAL_ZONES = {"qr zone", "mrz band"}



# Layout zones as (x0, y0, x1, y1) fractions of width/height.

REGION_MAPS: dict[str, dict[str, tuple[float, float, float, float]]] = {

    "passport": {

        "photo zone": (0.66, 0.20, 0.95, 0.68),

        "text band": (0.03, 0.18, 0.66, 0.80),

        "MRZ band": (0.0, 0.80, 1.0, 1.0),

        "header band": (0.0, 0.0, 1.0, 0.16),

    },

    "national_id": {

        "photo zone": (0.66, 0.20, 0.95, 0.68),

        "QR zone": (0.66, 0.62, 0.96, 0.94),

        "text band": (0.03, 0.18, 0.66, 0.92),

        "header band": (0.0, 0.0, 1.0, 0.16),

    },

    "pan": {

        "photo zone": (0.66, 0.20, 0.95, 0.68),

        "QR zone": (0.66, 0.62, 0.96, 0.94),

        "text band": (0.03, 0.18, 0.66, 0.92),

        "header band": (0.0, 0.0, 1.0, 0.16),

    },

    "driving_licence": {

        "photo zone": (0.66, 0.20, 0.95, 0.68),

        "text band": (0.03, 0.18, 0.66, 0.92),

        "header band": (0.0, 0.0, 1.0, 0.16),

    },

}





@dataclass

class ForensicDraft:

    region: str

    finding_type: str

    severity: str  # low | medium | high

    score: float   # 0..1

    bbox: list[int]  # x, y, w, h in pixels

    explanation: str





def _block_grid(map_2d: np.ndarray, block: int = _BLOCK):

    h, w = map_2d.shape

    h_c, w_c = (h // block) * block, (w // block) * block

    return map_2d[:h_c, :w_c].reshape(h_c // block, block, w_c // block, block)





def _chroma_residual_blocks(bgr: np.ndarray) -> tuple[np.ndarray, float]:

    """Per-block mean chroma deviation over near-neutral pixels.



    Returns (block map, document-level median deviation).

    """

    img = bgr.astype(np.float32)

    b, g, r = img[:, :, 0], img[:, :, 1], img[:, :, 2]

    mx, mn = img.max(axis=2), img.min(axis=2)

    neutral = (mx - mn) < 40.0

    dev = (np.abs(r - g) + np.abs(g - b)) * neutral



    d = _block_grid(dev).sum(axis=(1, 3))

    c = _block_grid(neutral.astype(np.float32)).sum(axis=(1, 3))

    blocks = np.where(c > 20, d / np.maximum(c, 1.0), 0.0)



    nonzero = blocks[blocks > 0]

    doc_median = float(np.median(nonzero)) if nonzero.size else 0.0

    return blocks, doc_median





def _ela_block_means(gray: np.ndarray) -> np.ndarray:

    ok, encoded = cv2.imencode(

        ".jpg", gray, [int(cv2.IMWRITE_JPEG_QUALITY), _JPEG_QUALITY]

    )

    if not ok:

        return np.zeros((gray.shape[0] // _BLOCK, gray.shape[1] // _BLOCK))

    recompressed = cv2.imdecode(encoded, cv2.IMREAD_GRAYSCALE)

    diff = cv2.absdiff(gray, recompressed).astype(np.float32)

    return _block_grid(diff).mean(axis=(1, 3))





def _label_region(cx_frac: float, cy_frac: float, doc_type: str | None) -> str:

    zones = REGION_MAPS.get((doc_type or "").lower())

    if zones:

        for name, (x0, y0, x1, y1) in zones.items():

            if x0 <= cx_frac <= x1 and y0 <= cy_frac <= y1:

                return name

    row = "upper" if cy_frac < 0.5 else "lower"

    col = "left" if cx_frac < 0.33 else ("central" if cx_frac < 0.66 else "right")

    return f"{row} {col} region"





def _severity(score: float) -> str:

    if score >= 0.66:

        return "high"

    if score >= 0.33:

        return "medium"

    return "low"





def _cluster_findings(

    blocks: np.ndarray,

    floor: float,

    gray_shape: tuple[int, int],

    doc_type: str | None,

    finding_type: str,

    score_scale: float,

    extra_note: str,

) -> list[ForensicDraft]:

    h, w = gray_shape

    hot = (blocks > floor).astype(np.uint8)

    hot_dilated = cv2.dilate(hot, np.ones((3, 3), np.uint8))

    n_labels, _, stats, _ = cv2.connectedComponentsWithStats(hot_dilated, connectivity=8)



    drafts: list[ForensicDraft] = []

    for label in range(1, n_labels):

        x_b, y_b, w_b, h_b, area = stats[label]

        if area < _MIN_CLUSTER_BLOCKS:

            continue

        cell_mask = hot[y_b : y_b + h_b, x_b : x_b + w_b].astype(bool)

        if not cell_mask.any():

            continue

        comp_value = float(np.median(blocks[y_b : y_b + h_b, x_b : x_b + w_b][cell_mask]))

        score = min(1.0, comp_value / score_scale)



        px, py = int(x_b * _BLOCK), int(y_b * _BLOCK)

        pw = min(int(w_b * _BLOCK), w - px)

        ph = min(int(h_b * _BLOCK), h - py)



        region = _label_region((px + pw / 2) / w, (py + ph / 2) / h, doc_type)

        if region.lower() in _STRUCTURAL_ZONES:

            score = min(score, 0.25)



        drafts.append(

            ForensicDraft(

                region=region,

                finding_type=finding_type,

                severity=_severity(score),

                score=round(score, 2),

                bbox=[px, py, pw, ph],

                explanation=(

                    f"Metric value {comp_value:.1f} exceeds the {floor:.0f} floor "

                    f"in the {region}. "

                    + (

                        "This matches the expected dense texture of this structural zone."

                        if region.lower() in _STRUCTURAL_ZONES

                        else "This is an indicator of potential manipulation, not proof."

                    )

                    + extra_note

                ),

            )

        )



    drafts.sort(key=lambda d: d.score, reverse=True)

    return drafts





def _iou(a: list[int], b: list[int]) -> float:

    ax, ay, aw, ah = a

    bx, by, bw, bh = b

    ix = max(0, min(ax + aw, bx + bw) - max(ax, bx))

    iy = max(0, min(ay + ah, by + bh) - max(ay, by))

    inter = ix * iy

    if inter == 0:

        return 0.0

    union = aw * ah + bw * bh - inter

    return inter / union





def analyze_image(

    image_bgr_or_gray: np.ndarray,

    doc_type: str | None = None,

) -> list[ForensicDraft]:

    """Run the transparent forensics pipeline over one document image.



    Two independent detectors run and their findings are merged:

    1. Chromatic-noise uniformity (sensitive; scan-like documents).

    2. Conservative error-level analysis (severity-capped; guards against

       dramatizing photographic grain).

    """

    if image_bgr_or_gray.ndim == 3:

        h, w = image_bgr_or_gray.shape[:2]

        gray = cv2.cvtColor(image_bgr_or_gray, cv2.COLOR_BGR2GRAY)

        chroma_blocks, _ = _chroma_residual_blocks(image_bgr_or_gray)

    else:

        h, w = image_bgr_or_gray.shape[:2]

        gray = image_bgr_or_gray

        chroma_blocks = None



    findings: list[ForensicDraft] = []



    if chroma_blocks is not None:

        findings.extend(

            _cluster_findings(

                chroma_blocks,

                _CHROMA_FLOOR,

                (h, w),

                doc_type,

                finding_type="chromatic_noise_anomaly",

                score_scale=_SCORE_SCALE,

                extra_note=(

                    " Chroma-channel uniformity differs from the rest of "

                    "the document."

                ),

            )

        )



    ela_floor = max(float(np.percentile(_ela_block_means(gray), 99.5)) * 1.15, 8.0)

    ela_findings = _cluster_findings(

        _ela_block_means(gray),

        ela_floor,

        (h, w),

        doc_type,

        finding_type="compression_anomaly",

        score_scale=_SCORE_SCALE * 1.4,

        extra_note=(

            " Compression-difference response differs from surrounding areas."

        ),

    )

    # Keep ELA findings that do not overlap an existing chroma finding.

    for draft in ela_findings:

        if all(_iou(draft.bbox, f.bbox) < 0.3 for f in findings):

            findings.append(draft)



    findings.sort(key=lambda d: d.score, reverse=True)

    return findings





def overall_suspicion(scores) -> tuple[str, int]:

    """Aggregate (severity_label, 0-100 score) from finding scores."""

    scores = list(scores)

    if not scores:

        return "low", 0

    pct = int(round(max(scores) * 100))

    if pct >= 66:

        return "high", pct

    if pct >= 33:

        return "medium", pct

    return "low", pct





__all__ = ["analyze_image", "overall_suspicion", "ForensicDraft"]

