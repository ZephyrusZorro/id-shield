"""Face extraction & cross-matching unit tests."""
from pathlib import Path
import numpy as np
import cv2
import pytest

from app.services import face_service
from app.services.face_service import (
    FaceCropResult,
    compare_two_faces,
    compare_document_faces,
    extract_face,
)


def _create_mock_face(color=(200, 180, 160), hair_color=(30, 20, 20)) -> np.ndarray:
    """Create a synthetic image with a clear face."""
    img = np.full((600, 800, 3), 245, dtype=np.uint8)
    # Face in photo zone
    cx, cy = 600, 300
    # Torso
    cv2.ellipse(img, (cx, 450), (120, 90), 0, 0, 360, (50, 80, 140), -1)
    # Neck
    cv2.rectangle(img, (cx - 25, 320), (cx + 25, 400), color, -1)
    # Head
    cv2.ellipse(img, (cx, cy), (65, 85), 0, 0, 360, color, -1)
    # Hair
    cv2.ellipse(img, (cx, cy - 40), (68, 50), 0, 180, 360, hair_color, -1)
    # Eyes
    cv2.circle(img, (cx - 22, cy - 10), 6, (255, 255, 255), -1)
    cv2.circle(img, (cx - 22, cy - 10), 3, (10, 10, 10), -1)
    cv2.circle(img, (cx + 22, cy - 10), 6, (255, 255, 255), -1)
    cv2.circle(img, (cx + 22, cy - 10), 3, (10, 10, 10), -1)
    # Eyebrows
    cv2.line(img, (cx - 30, cy - 20), (cx - 14, cy - 20), hair_color, 2)
    cv2.line(img, (cx + 14, cy - 20), (cx + 30, cy - 20), hair_color, 2)
    # Nose
    cv2.line(img, (cx, cy), (cx - 4, cy + 15), (160, 140, 120), 2)
    cv2.line(img, (cx - 4, cy + 15), (cx + 4, cy + 15), (160, 140, 120), 2)
    # Mouth
    cv2.ellipse(img, (cx, cy + 35), (16, 8), 0, 0, 180, (140, 60, 60), 2)
    return img


def test_extract_face_from_mock_image(tmp_path: Path):
    img = _create_mock_face()
    res = extract_face(img, doc_id="doc1", file_name="passport.png", doc_type="passport", save_crop_dir=tmp_path)
    assert res is not None
    assert res.document_id == "doc1"
    assert len(res.bbox) == 4
    assert res.sharpness >= 0
    assert "phash" in res.features
    assert (tmp_path / "doc1_face.png").is_file()


def test_matching_faces_produce_high_similarity(tmp_path: Path):
    img_a = _create_mock_face(color=(210, 190, 170), hair_color=(30, 20, 20))
    img_b = _create_mock_face(color=(205, 185, 165), hair_color=(30, 20, 20))

    path_a = tmp_path / "doc_a.png"
    path_b = tmp_path / "doc_b.png"
    cv2.imwrite(str(path_a), img_a)
    cv2.imwrite(str(path_b), img_b)

    face_a = extract_face(img_a, "a", "passport.png", "passport", tmp_path)
    face_b = extract_face(img_b, "b", "national_id.png", "national_id", tmp_path)

    assert face_a is not None and face_b is not None
    cmp = compare_two_faces(face_a, face_b, path_a, path_b)
    assert cmp.similarity_score >= 70
    assert cmp.status == "match"
    assert cmp.severity == "info"


def test_different_faces_produce_mismatch(tmp_path: Path):
    # Face A: standard tone, dark hair
    img_a = _create_mock_face(color=(240, 220, 200), hair_color=(10, 10, 10))
    # Face B: distinctly different tone, blonde/light hair, different clothing
    img_b = np.full((600, 800, 3), 50, dtype=np.uint8)
    cv2.rectangle(img_b, (550, 200), (670, 380), (120, 80, 50), -1)
    cv2.circle(img_b, (610, 260), 20, (255, 255, 255), -1)

    path_a = tmp_path / "doc_a.png"
    path_b = tmp_path / "doc_b.png"
    cv2.imwrite(str(path_a), img_a)
    cv2.imwrite(str(path_b), img_b)

    face_a = extract_face(img_a, "a", "passport.png", "passport", tmp_path)
    face_b = extract_face(img_b, "b", "pan.png", "pan", tmp_path)

    assert face_a is not None and face_b is not None
    cmp = compare_two_faces(face_a, face_b, path_a, path_b)
    assert cmp.similarity_score < 70
    assert cmp.status in ("borderline", "mismatch")
