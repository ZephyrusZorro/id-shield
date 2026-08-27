"""Duplicate / reuse detection.

Signals:
- exact reuse: identical SHA-256 file hash anywhere else in the system
- perceptual reuse: near-identical imagery (average-hash Hamming distance)

A hit means this identity evidence was already submitted before — a reuse
indicator, not proof of fraud on its own.
"""
from __future__ import annotations

import imagehash
from PIL import Image

PERCEPTUAL_DISTANCE_THRESHOLD = 8  # 64-bit average hash bits


def perceptual_hash_of(gray_image) -> str:
    """Average perceptual hash (64-bit hex) from a grayscale ndarray."""
    return str(imagehash.average_hash(Image.fromarray(gray_image)))


def hamming_distance(hex_a: str, hex_b: str) -> int | None:
    try:
        return imagehash.hex_to_hash(hex_a) - imagehash.hex_to_hash(hex_b)
    except (ValueError, TypeError):
        return None


def find_reuse(
    file_hash: str | None,
    perceptual: str | None,
    others: list,
    use_perceptual: bool = True,
) -> list[dict]:
    """Compare one document against all other documents.

    `others` items need: id, case_id, file_name, file_hash, perceptual_hash.
    Returns [{document_id, case_id, kind}] where kind is exact|perceptual.

    Note: perceptual matching is OFF by default in the pipeline because
    flat scan-style documents (mostly white) produce near-identical average
    hashes regardless of content, flooding results with false positives.
    Exact SHA-256 reuse remains the reliable MVP signal.
    """
    hits: list[dict] = []
    seen_ids: set[str] = set()
    for other in others:
        if other.file_hash and file_hash and other.file_hash == file_hash:
            hits.append(
                {"document_id": other.id, "case_id": other.case_id, "kind": "exact"}
            )
            seen_ids.add(other.id)
        elif (
            use_perceptual
            and other.id not in seen_ids
            and perceptual
            and other.perceptual_hash
        ):
            dist = hamming_distance(perceptual, other.perceptual_hash)
            if dist is not None and dist <= PERCEPTUAL_DISTANCE_THRESHOLD:
                hits.append(
                    {
                        "document_id": other.id,
                        "case_id": other.case_id,
                        "kind": "perceptual",
                    }
                )
                seen_ids.add(other.id)
    return hits
