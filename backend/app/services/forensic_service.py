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





def _detect_metadata_tampering(file_path, w: int, h: int) -> list[ForensicDraft]:
    """Inspect file header and metadata for photo editing software signatures."""
    if file_path is None:
        return []
    from pathlib import Path
    p = Path(file_path)
    if not p.is_file():
        return []

    detected_tools: list[str] = []
    suspicious_keywords = [
        "photoshop", "gimp", "canva", "picsart", "pixelmator",
        "paint.net", "coreldraw", "inkscape", "affinity", "illustrator"
    ]

    try:
        # Read header and trailer bytes
        raw_content = b""
        with open(p, "rb") as fh:
            raw_content = fh.read(65536).lower()
        for kw in suspicious_keywords:
            if kw.encode("latin-1") in raw_content:
                detected_tools.append(kw.capitalize())

        # Inspect PIL metadata
        try:
            from PIL import Image
            with Image.open(p) as pil_img:
                info_str = str(pil_img.info).lower()
                for kw in suspicious_keywords:
                    if kw in info_str and kw.capitalize() not in detected_tools:
                        detected_tools.append(kw.capitalize())
                exif = pil_img.getexif()
                if exif:
                    for tag_id, val in exif.items():
                        v_str = str(val).lower()
                        for kw in suspicious_keywords:
                            if kw in v_str and kw.capitalize() not in detected_tools:
                                detected_tools.append(kw.capitalize())
        except Exception:
            pass
    except Exception:
        pass

    if not detected_tools:
        return []

    tools_str = ", ".join(sorted(set(detected_tools)))
    return [
        ForensicDraft(
            region="header band",
            finding_type="metadata_tamper_indicator",
            severity="high",
            score=0.85,
            bbox=[0, 0, w, max(24, int(h * 0.12))],
            explanation=(
                f"Document metadata or file header contains image editing software signature "
                f"('{tools_str}'). This indicates the document was digitally manipulated, "
                f"re-rendered, or modified in post-processing software."
            ),
        )
    ]


def _detect_copy_move(gray: np.ndarray, doc_type: str | None) -> list[ForensicDraft]:
    """Detect duplicated patches/elements within the document using ORB feature matching."""
    h, w = gray.shape[:2]
    if h < 200 or w < 200:
        return []

    try:
        orb = cv2.ORB_create(nfeatures=600, fastThreshold=15)
        kp, des = orb.detectAndCompute(gray, None)
        if des is None or len(kp) < 15:
            return []

        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        matches = bf.knnMatch(des, des, k=3)

        good_pairs = []
        for m in matches:
            if len(m) > 1:
                cand = m[1]
                if cand.distance < 28:
                    pt1 = kp[cand.queryIdx].pt
                    pt2 = kp[cand.trainIdx].pt
                    dx = pt1[0] - pt2[0]
                    dy = pt1[1] - pt2[1]
                    dist = float(np.hypot(dx, dy))
                    if 60.0 < dist < (max(w, h) * 0.85):
                        good_pairs.append((pt1, pt2, (round(dx / 12) * 12, round(dy / 12) * 12)))

        if not good_pairs:
            return []

        from collections import Counter
        vectors = [p[2] for p in good_pairs]
        counts = Counter(vectors)
        top_vector, top_count = counts.most_common(1)[0]

        if top_count >= 5:
            # Avoid false-positive on repetitive document lines / text paragraphs
            dx_v, dy_v = top_vector
            if abs(dx_v) <= 12 and bw > w * 0.45:
                return []

            matched_pts = [p[0] for p in good_pairs if p[2] == top_vector]
            xs = [int(p[0]) for p in matched_pts]
            ys = [int(p[1]) for p in matched_pts]
            min_x, max_x = max(0, min(xs) - 16), min(w, max(xs) + 16)
            min_y, max_y = max(0, min(ys) - 16), min(h, max(ys) + 16)
            bw = max_x - min_x
            bh = max_y - min_y

            # Recheck width after matched_pts
            if abs(dx_v) <= 12 and bw > w * 0.45:
                return []

            score = min(0.85, 0.45 + (top_count * 0.05))
            region = _label_region((min_x + bw / 2) / w, (min_y + bh / 2) / h, doc_type)
            if region.lower() in _STRUCTURAL_ZONES:
                score = min(score, 0.25)

            return [
                ForensicDraft(
                    region=region,
                    finding_type="copy_move_anomaly",
                    severity=_severity(score),
                    score=round(score, 2),
                    bbox=[min_x, min_y, bw, bh],
                    explanation=(
                        f"Detected {top_count} duplicated visual features with identical spatial "
                        f"displacement in the {region}. This is an indicator of potential manipulation, not proof."
                    ),
                )
            ]
    except Exception:
        pass
    return []


def _detect_noise_inconsistency(gray: np.ndarray, doc_type: str | None) -> list[ForensicDraft]:
    """Detect regions whose high-frequency sensor noise standard deviation is statistically anomalous."""
    h, w = gray.shape[:2]
    if h < 200 or w < 200:
        return []

    try:
        blur = cv2.medianBlur(gray, 3)
        res = cv2.absdiff(gray, blur).astype(np.float32)

        h_c, w_c = (h // _BLOCK) * _BLOCK, (w // _BLOCK) * _BLOCK
        if h_c < _BLOCK * 4 or w_c < _BLOCK * 4:
            return []

        grid = res[:h_c, :w_c].reshape(h_c // _BLOCK, _BLOCK, w_c // _BLOCK, _BLOCK)
        block_stds = grid.std(axis=(1, 3))

        grad_x = cv2.Sobel(gray[:h_c, :w_c], cv2.CV_32F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(gray[:h_c, :w_c], cv2.CV_32F, 0, 1, ksize=3)
        edge_mag = np.hypot(grad_x, grad_y)
        edge_grid = edge_mag.reshape(h_c // _BLOCK, _BLOCK, w_c // _BLOCK, _BLOCK)
        block_edges = (edge_grid > 50).sum(axis=(1, 3))

        substrate_mask = block_edges < 35
        if substrate_mask.sum() < 20:
            return []

        substrate_stds = block_stds[substrate_mask]
        doc_noise_median = float(np.median(substrate_stds))

        if doc_noise_median < 1.8:
            return []

        anom_blocks = (block_stds > (doc_noise_median * 3.0)) & substrate_mask
        if anom_blocks.sum() < _MIN_CLUSTER_BLOCKS:
            return []

        return _cluster_findings(
            block_stds,
            floor=doc_noise_median * 2.6,
            gray_shape=(h, w),
            doc_type=doc_type,
            finding_type="noise_variance_anomaly",
            score_scale=doc_noise_median * 4.8,
            extra_note=" Local high-frequency sensor noise standard deviation diverges significantly from surrounding substrate.",
        )
    except Exception:
        return []


def _detect_suspicious_text_replacement(gray: np.ndarray, doc_type: str | None) -> list[ForensicDraft]:
    """Detect suspicious text replacement indicators.

    Identifies localized text patches with background luminance discontinuity,
    font thickness/sharpness disparity, or rectangular bounding box boundaries.
    """
    h, w = gray.shape[:2]
    if h < 250 or w < 250:
        return []

    try:
        # 1. Binarize to isolate candidate text components
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 21, 10
        )

        # Morphological dilation horizontally to merge letters into words/field boxes
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 3))
        dilated = cv2.morphologyEx(thresh, cv2.MORPH_DILATE, kernel)

        # Global document background estimate (pixels that are non-text)
        non_text_mask = thresh == 0
        if non_text_mask.sum() < 1000:
            return []
        global_bg_median = float(np.median(gray[non_text_mask]))

        # Find connected components (candidate text field boxes)
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(dilated, connectivity=8)

        drafts = []
        for i in range(1, num_labels):
            x, y, bw, bh, area = stats[i]
            # Filter for plausible identity field text regions (e.g. name, DOB, ID number)
            if bw < 50 or bh < 12 or bw > w * 0.75 or bh > 90 or area < 200:
                continue

            # Check local background surrounding the text inside the bbox
            patch = gray[y : y + bh, x : x + bw]
            patch_non_text = thresh[y : y + bh, x : x + bw] == 0
            if patch_non_text.sum() < 50:
                continue

            local_bg = float(np.median(patch[patch_non_text]))
            bg_diff = abs(local_bg - global_bg_median)

            # Legitimate paper substrates are light (typically > 170).
            # Text replacement patches occur when a white/off-white patch is pasted onto paper.
            if global_bg_median < 170 or local_bg < 170:
                continue

            # Check boundary gradient step (rectangular halo artifact from pasted text patch)
            pad = 4
            y0, y1 = max(0, y - pad), min(h, y + bh + pad)
            x0, x1 = max(0, x - pad), min(w, x + bw + pad)
            surrounding = gray[y0:y1, x0:x1]
            if surrounding.size < 100:
                continue

            surr_grad_y = np.abs(cv2.Sobel(surrounding, cv2.CV_32F, 0, 1, ksize=3))
            surr_grad_x = np.abs(cv2.Sobel(surrounding, cv2.CV_32F, 1, 0, ksize=3))
            box_edge_strength = float(np.mean(surr_grad_y) + np.mean(surr_grad_x))

            # Must have noticeable background shift on substrate AND perimeter step edge
            if bg_diff > 28.0 and box_edge_strength > 35.0:
                score = min(0.85, 0.40 + (bg_diff / 50.0) * 0.35)
                region = _label_region((x + bw / 2) / w, (y + bh / 2) / h, doc_type)
                if region.lower() in _STRUCTURAL_ZONES:
                    score = min(score, 0.25)
                drafts.append(
                    ForensicDraft(
                        region=region,
                        finding_type="suspicious_text_replacement",
                        severity=_severity(score),
                        score=round(score, 2),
                        bbox=[int(x), int(y), int(bw), int(bh)],
                        explanation=(
                            f"Suspicious text region detected in {region}: localized background luminance "
                            f"divergence (Δ {bg_diff:.1f}) and boundary step-edge contrast around text block. "
                            f"This is an indicator of potential manipulation, not proof."
                        ),
                    )
                )

        drafts.sort(key=lambda d: d.score, reverse=True)
        return drafts[:3]
    except Exception:
        return []


def analyze_image(
    image_bgr_or_gray: np.ndarray,
    doc_type: str | None = None,
    file_path=None,
) -> list[ForensicDraft]:
    """Run the transparent forensics pipeline over one document image.

    Detectors run and their findings are merged:
    1. Chromatic-noise uniformity (sensitive; scan-like documents).
    2. Conservative error-level analysis (severity-capped; guards against dramatizing photographic grain).
    3. High-frequency sensor noise variance inconsistency.
    4. Copy-move / clone-stamp feature duplication.
    5. Image metadata / EXIF software editing signature audit.
    6. Suspicious text replacement / patch detection.
    """
    h, w = image_bgr_or_gray.shape[:2]
    if h < 100 or w < 100:
        return []

    if image_bgr_or_gray.ndim == 3:
        gray = cv2.cvtColor(image_bgr_or_gray, cv2.COLOR_BGR2GRAY)
        chroma_blocks, _ = _chroma_residual_blocks(image_bgr_or_gray)
    else:
        gray = image_bgr_or_gray
        chroma_blocks = None

    findings: list[ForensicDraft] = []

    # 1. Chromatic-noise uniformity
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
                    " Chroma-channel uniformity differs from the rest of the document."
                ),
            )
        )

    # 2. Error-Level Analysis (ELA)
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
    for draft in ela_findings:
        if all(_iou(draft.bbox, f.bbox) < 0.3 for f in findings):
            findings.append(draft)

    # 3. High-frequency noise variance anomaly
    noise_findings = _detect_noise_inconsistency(gray, doc_type)
    for draft in noise_findings:
        if all(_iou(draft.bbox, f.bbox) < 0.35 for f in findings):
            findings.append(draft)

    # 4. Copy-Move / Duplication detection
    cm_findings = _detect_copy_move(gray, doc_type)
    for draft in cm_findings:
        if all(_iou(draft.bbox, f.bbox) < 0.35 for f in findings):
            findings.append(draft)

    # 5. Suspicious text replacement
    text_findings = _detect_suspicious_text_replacement(gray, doc_type)
    for draft in text_findings:
        if all(_iou(draft.bbox, f.bbox) < 0.3 for f in findings):
            findings.append(draft)

    # 6. Metadata / Software tamper detection
    meta_findings = _detect_metadata_tampering(file_path, w, h)
    findings.extend(meta_findings)

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

