"""Pluggable OCR layer.

Priority order:
1. Tesseract (pytesseract) — primary, installed locally.
2. EasyOCR — fallback if pip-installed and models available.
3. OcrUnavailableError — pipeline surfaces an honest 'unavailable' state.

The interface never fabricates results: callers must handle unavailability.
"""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import numpy as np

from app.core.logging import get_logger

log = get_logger("idshield.ocr")

_KNOWN_TESSERACT_PATHS = [
    Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
    Path(os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe")),
    Path("/usr/bin/tesseract"),
    Path("/opt/homebrew/bin/tesseract"),
]


class OcrUnavailableError(RuntimeError):
    """No OCR engine is usable in this environment."""


@dataclass
class Word:
    text: str
    confidence: float  # 0..100
    bbox: tuple[int, int, int, int]  # x, y, w, h


@dataclass
class Line:
    text: str
    confidence: float  # 0..100
    bbox: tuple[int, int, int, int]
    words: list[Word] = field(default_factory=list)


@dataclass
class OcrResult:
    lines: list[Line]
    engine: str
    mean_confidence: float | None
    full_text: str


def _find_tesseract() -> str | None:
    cmd = os.environ.get("TESSERACT_CMD")
    if cmd and Path(cmd).is_file():
        return cmd
    for path in _KNOWN_TESSERACT_PATHS:
        if path.is_file():
            return str(path)
    which = shutil.which("tesseract")
    return which


class TesseractBackend:
    name = "tesseract"

    def __init__(self, cmd: str) -> None:
        self._cmd = cmd

    def _run_single(self, image_bgr: np.ndarray) -> OcrResult:
        import cv2
        import pytesseract

        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        data = pytesseract.image_to_data(
            rgb,
            output_type=pytesseract.Output.DICT,
            config="--oem 3 --psm 6",
        )

        groups: dict[tuple, list[Word]] = {}
        n = len(data["text"])
        for i in range(n):
            raw_text = (data["text"][i] or "").strip()
            conf_raw = data["conf"][i]
            try:
                conf = float(conf_raw)
            except (TypeError, ValueError):
                conf = -1.0
            if not raw_text or conf < 0:
                continue
            key = (
                data["block_num"][i],
                data["par_num"][i],
                data["line_num"][i],
            )
            word = Word(
                text=raw_text,
                confidence=conf,
                bbox=(
                    int(data["left"][i]),
                    int(data["top"][i]),
                    int(data["width"][i]),
                    int(data["height"][i]),
                ),
            )
            groups.setdefault(key, []).append(word)

        lines: list[Line] = []
        for words in groups.values():
            xs = [w.bbox[0] for w in words]
            ys = [w.bbox[1] for w in words]
            rights = [w.bbox[0] + w.bbox[2] for w in words]
            bottoms = [w.bbox[1] + w.bbox[3] for w in words]
            lines.append(
                Line(
                    text=" ".join(w.text for w in words),
                    confidence=sum(w.confidence for w in words) / len(words),
                    bbox=(min(xs), min(ys), max(rights) - min(xs), max(bottoms) - min(ys)),
                    words=words,
                )
            )
        # Reorder top-to-bottom for natural reading order.
        lines.sort(key=lambda l: (l.bbox[1], l.bbox[0]))
        return lines

    def _merge_lines(self, line_groups: list[list[Line]]) -> list[Line]:
        merged: list[Line] = []
        seen_keys: set[tuple] = set()
        for group in line_groups:
            for line in group:
                key = (line.text.lower().strip(), round(line.bbox[1] / 12))
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                merged.append(line)
        merged.sort(key=lambda l: (l.bbox[1], l.bbox[0]))
        return merged

    def run(self, image_bgr: np.ndarray) -> OcrResult:
        """Multi-pass OCR: full page (normal + inverted) plus an upscaled
        bottom strip, where machine-readable zones conventionally live."""
        import cv2

        groups = [self._run_single(image_bgr)]
        groups.append(self._run_single(cv2.bitwise_not(image_bgr)))

        h, w = image_bgr.shape[:2]
        strip = image_bgr[int(h * 0.70) :, :]
        if strip.size and w < 2200:
            scale = 2200 / w
            strip = cv2.resize(
                strip, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC
            )
        if strip.size:
            groups.append(self._run_single(strip))

        merged = self._merge_lines(groups)
        all_confs = [w.confidence for l in merged for w in l.words]
        mean_conf = round(sum(all_confs) / len(all_confs), 1) if all_confs else None
        return OcrResult(
            lines=merged,
            engine=self.name,
            mean_confidence=mean_conf,
            full_text="\n".join(l.text for l in merged),
        )


class EasyOcrBackend:
    name = "easyocr"

    def __init__(self) -> None:
        import easyocr  # heavy import, deferred

        self._reader = easyocr.Reader(["en"], gpu=False, verbose=False)

    def run(self, image_bgr: np.ndarray) -> OcrResult:
        results = self._reader.readtext(image_bgr)
        lines: list[Line] = []
        for box, text, conf in results:
            xs = [int(p[0]) for p in box]
            ys = [int(p[1]) for p in box]
            lines.append(
                Line(
                    text=text.strip(),
                    confidence=float(conf) * 100.0,
                    bbox=(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)),
                    words=[],
                )
            )
        lines.sort(key=lambda l: (l.bbox[1], l.bbox[0]))
        all_confs = [l.confidence for l in lines]
        mean_conf = round(sum(all_confs) / len(all_confs), 1) if all_confs else None
        return OcrResult(
            lines=lines,
            engine=self.name,
            mean_confidence=mean_conf,
            full_text="\n".join(l.text for l in lines),
        )


@lru_cache(maxsize=1)
def get_backend():
    """Return the best available OCR backend, or raise OcrUnavailableError."""
    tesseract_cmd = _find_tesseract()
    if tesseract_cmd:
        import pytesseract

        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        log.info("OCR_BACKEND_SELECTED | engine=tesseract")
        return TesseractBackend(tesseract_cmd)

    try:
        import easyocr  # noqa: F401

        log.info("OCR_BACKEND_SELECTED | engine=easyocr")
        return EasyOcrBackend()
    except ImportError:
        pass

    raise OcrUnavailableError(
        "No OCR engine is available. Install Tesseract or EasyOCR."
    )
