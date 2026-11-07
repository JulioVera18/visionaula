"""Fixtures compartidas.

FakeEngine reemplaza a las redes de OpenCV en las pruebas de Django para que
sean deterministas (no dependen de una cámara ni de un rostro real).
"""

import cv2
import numpy as np
import pytest

from asistencia import services
from asistencia.models import Estudiante
from vision.detector import FaceDetection
from vision.pipeline import EnrollmentError, EnrollmentSample, FaceResult, FrameAnalysis
from vision.preprocessing import FaceQuality
from vision.recognizer import Match, normalize


def make_jpeg(width: int = 320, height: int = 240, value: int = 128) -> bytes:
    image = np.full((height, width, 3), value, dtype=np.uint8)
    cv2.rectangle(image, (40, 40), (120, 140), (200, 180, 160), -1)
    ok, buffer = cv2.imencode(".jpg", image)
    assert ok
    return buffer.tobytes()


class FakeEngine:
    """Simula FaceEngine: reconoce siempre al estudiante configurado."""

    def __init__(self, label=None, similarity=0.85, enrollment_error=None):
        self.label = label
        self.similarity = similarity
        self.enrollment_error = enrollment_error

    def analyze(self, image, gallery, threshold=0.4):
        face = FaceResult(
            box=(40, 40, 80, 100),
            score=0.95,
            landmarks=((60, 70), (100, 70), (80, 90), (65, 115), (95, 115)),
            match=Match(label=self.label, similarity=self.similarity),
            face_crop=image[40:140, 40:120].copy(),
        )
        return FrameAnalysis(image=image, faces=(face,), low_light=False, elapsed_ms=5.0)

    def enrollment_sample(self, image):
        if self.enrollment_error:
            raise EnrollmentError(self.enrollment_error)
        rng = np.random.default_rng(0)
        return EnrollmentSample(
            embedding=normalize(rng.normal(size=128)),
            face_crop=image[40:140, 40:120].copy(),
            quality=FaceQuality(sharpness=120.0, brightness=130.0, ok=True),
        )


@pytest.fixture(autouse=True)
def media_tmp(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"
    settings.STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }


@pytest.fixture(autouse=True)
def fresh_state(monkeypatch):
    services.get_tracker.reset()
    monkeypatch.setattr(services, "gallery_cache", services.GalleryCache())
    yield
    services.get_tracker.reset()


@pytest.fixture
def jpeg_bytes():
    return make_jpeg()


@pytest.fixture
def docente(django_user_model):
    return django_user_model.objects.create_user("docente", password="Clave-Segura-123")


@pytest.fixture
def cliente(client, docente):
    client.force_login(docente)
    return client


@pytest.fixture
def estudiante(db):
    return Estudiante.objects.create(codigo="0912345678", nombres="Ana", apellidos="Pérez")


@pytest.fixture
def fake_engine(monkeypatch):
    engine = FakeEngine()
    monkeypatch.setattr(services, "get_engine", lambda: engine)
    return engine


@pytest.fixture
def detection():
    raw = np.array(
        [40, 40, 80, 100, 60, 70, 100, 70, 80, 90, 65, 115, 95, 115, 0.95], dtype=np.float32
    )
    return FaceDetection(
        box=(40, 40, 80, 100),
        score=0.95,
        landmarks=((60, 70), (100, 70), (80, 90), (65, 115), (95, 115)),
        raw=raw,
    )
