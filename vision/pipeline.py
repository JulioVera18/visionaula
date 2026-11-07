"""Orquestación del pipeline: procesamiento -> detección -> reconocimiento -> anotación."""

import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from . import annotator, preprocessing
from .detector import FaceDetector, crop
from .recognizer import DEFAULT_THRESHOLD, FaceEmbedder, Gallery, Match, match

PROCESSING_MAX_SIDE = 960


@dataclass(frozen=True)
class FaceResult:
    box: tuple
    score: float
    landmarks: tuple
    match: Match
    face_crop: np.ndarray = field(repr=False, compare=False)


@dataclass(frozen=True)
class FrameAnalysis:
    image: np.ndarray = field(repr=False, compare=False)
    faces: tuple
    low_light: bool
    elapsed_ms: float

    @property
    def known(self) -> tuple:
        return tuple(face for face in self.faces if face.match.is_known)

    @property
    def unknown_count(self) -> int:
        return len(self.faces) - len(self.known)


@dataclass(frozen=True)
class EnrollmentSample:
    embedding: np.ndarray = field(repr=False)
    face_crop: np.ndarray = field(repr=False)
    quality: preprocessing.FaceQuality


class EnrollmentError(ValueError):
    """La imagen no sirve como muestra de registro (mensaje apto para el usuario)."""


class FaceEngine:
    """Envuelve las redes DNN de OpenCV. Las redes no son seguras entre hilos,
    por eso cada inferencia se protege con un candado."""

    def __init__(self, detector: FaceDetector, embedder: FaceEmbedder):
        self._detector = detector
        self._embedder = embedder
        self._lock = threading.Lock()

    @classmethod
    def from_models(
        cls, yunet: Path, sface: Path, score_threshold: float = 0.8, min_face_size: int = 40
    ) -> "FaceEngine":
        detector = FaceDetector(yunet, score_threshold=score_threshold, min_face_size=min_face_size)
        return cls(detector, FaceEmbedder(sface))

    def analyze(
        self, image: np.ndarray, gallery: Gallery, threshold: float = DEFAULT_THRESHOLD
    ) -> FrameAnalysis:
        """Detecta y reconoce todos los rostros de un fotograma."""
        started = time.perf_counter()
        frame = preprocessing.resize_max_side(image, PROCESSING_MAX_SIDE)
        low_light = preprocessing.is_low_light(frame)
        working = preprocessing.enhance_lighting(frame) if low_light else frame
        with self._lock:
            detections = self._detector.detect(working)
            faces = tuple(
                FaceResult(
                    box=d.box,
                    score=d.score,
                    landmarks=d.landmarks,
                    match=match(gallery, self._embedder.embed(working, d), threshold),
                    face_crop=crop(frame, d.box),
                )
                for d in detections
            )
        elapsed = (time.perf_counter() - started) * 1000
        return FrameAnalysis(frame, faces, low_light, round(elapsed, 1))

    def enrollment_sample(self, image: np.ndarray) -> EnrollmentSample:
        """Extrae el embedding de una foto que debe contener exactamente un rostro."""
        frame = preprocessing.resize_max_side(image, PROCESSING_MAX_SIDE)
        if preprocessing.is_low_light(frame):
            frame = preprocessing.enhance_lighting(frame)
        with self._lock:
            detections = self._detector.detect(frame)
            if not detections:
                raise EnrollmentError("No se detectó ningún rostro.")
            if len(detections) > 1:
                raise EnrollmentError("Hay más de un rostro: solo el estudiante debe aparecer.")
            aligned = self._embedder.align(frame, detections[0])
            quality = preprocessing.assess_face_quality(aligned)
            if not quality.ok:
                raise EnrollmentError(quality.reason)
            embedding = self._embedder.embed_aligned(aligned)
        return EnrollmentSample(embedding, crop(frame, detections[0].box), quality)


@dataclass(frozen=True)
class RenderOptions:
    view_mode: str = "normal"
    privacy: bool = False
    show_landmarks: bool = True
    confirmed_labels: frozenset = frozenset()


def render(analysis: FrameAnalysis, names: dict, options: RenderOptions) -> np.ndarray:
    """Genera el fotograma anotado que se envía al navegador."""
    output = preprocessing.apply_view_filter(analysis.image, options.view_mode).copy()
    for face in analysis.faces:
        _draw_face(output, face, names, options)
    hud = [
        f"Rostros: {len(analysis.faces)}  Reconocidos: {len(analysis.known)}",
        f"Procesamiento: {analysis.elapsed_ms:.0f} ms",
    ]
    if analysis.low_light:
        hud.append("Poca luz: mejora CLAHE aplicada")
    annotator.draw_hud(output, hud)
    return output


def _draw_face(output: np.ndarray, face: FaceResult, names: dict, options: RenderOptions) -> None:
    label = face.match.label
    if label is None:
        if options.privacy:
            annotator.pixelate(output, face.box)
        color, text = annotator.COLOR_UNKNOWN, f"Desconocido {face.match.similarity:.2f}"
    else:
        confirmed = label in options.confirmed_labels
        color = annotator.COLOR_CONFIRMED if confirmed else annotator.COLOR_KNOWN
        mark = " [OK]" if confirmed else ""
        text = f"{names.get(label, label)} {face.match.similarity:.2f}{mark}"
    annotator.draw_corners(output, face.box, color)
    if options.show_landmarks:
        annotator.draw_landmarks(output, face.landmarks)
    x, y, _, _ = face.box
    annotator.draw_label(output, text, (x, y - 4), color)
