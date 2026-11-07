"""Pruebas con las redes reales YuNet y SFace (se omiten si no están descargadas)."""

import numpy as np
import pytest
from django.conf import settings

from vision.model_store import (
    MODELS, ModelUnavailableError, is_model_valid, model_path, require_model,
)
from vision.pipeline import EnrollmentError, FaceEngine
from vision.recognizer import EMPTY_GALLERY, FaceEmbedder

MODELS_DIR = settings.VISION["MODELS_DIR"]
MODELOS_PRESENTES = all(model_path(MODELS_DIR, k).is_file() for k in MODELS)

pytestmark = [
    pytest.mark.models,
    pytest.mark.skipif(not MODELOS_PRESENTES, reason="Ejecute manage.py descargar_modelos"),
]


@pytest.fixture(scope="module")
def engine():
    return FaceEngine.from_models(model_path(MODELS_DIR, "yunet"), model_path(MODELS_DIR, "sface"))


def test_downloaded_models_match_sha256():
    assert all(is_model_valid(MODELS_DIR, key) for key in MODELS)


def test_blank_frame_has_no_faces(engine):
    frame = np.full((480, 640, 3), 90, dtype=np.uint8)
    analysis = engine.analyze(frame, EMPTY_GALLERY)
    assert analysis.faces == ()
    assert analysis.elapsed_ms >= 0


def test_enrollment_without_face_is_rejected(engine):
    with pytest.raises(EnrollmentError, match="ningún rostro"):
        engine.enrollment_sample(np.full((480, 640, 3), 200, dtype=np.uint8))


def test_sface_produces_normalized_128d_embedding(detection):
    embedder = FaceEmbedder(model_path(MODELS_DIR, "sface"))
    rng = np.random.default_rng(7)
    image = rng.integers(0, 255, size=(240, 320, 3), dtype=np.uint8)
    vector = embedder.embed(image, detection)
    assert vector.shape == (128,)
    assert np.linalg.norm(vector) == pytest.approx(1.0, abs=1e-4)


def test_require_model_reports_missing_file(tmp_path):
    with pytest.raises(ModelUnavailableError, match="descargar_modelos"):
        require_model(tmp_path, "yunet")
