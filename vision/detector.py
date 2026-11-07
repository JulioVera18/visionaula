"""Detección de rostros con la red neuronal YuNet (cv2.FaceDetectorYN)."""

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


@dataclass(frozen=True)
class FaceDetection:
    """Rostro detectado.

    box: (x, y, ancho, alto) en píxeles.
    landmarks: 5 puntos (ojo der., ojo izq., nariz, comisura der., comisura izq.).
    raw: fila original de 15 valores que necesita FaceRecognizerSF.alignCrop.
    """

    box: tuple
    score: float
    landmarks: tuple
    raw: np.ndarray

    @property
    def area(self) -> int:
        return int(self.box[2] * self.box[3])


class FaceDetector:
    def __init__(
        self,
        model_path: Path,
        score_threshold: float = 0.8,
        nms_threshold: float = 0.3,
        top_k: int = 50,
        min_face_size: int = 40,
    ):
        self._min_face_size = min_face_size
        self._net = cv2.FaceDetectorYN.create(
            str(model_path), "", (320, 320), score_threshold, nms_threshold, top_k
        )

    def detect(self, image: np.ndarray) -> list:
        """Devuelve los rostros ordenados de mayor a menor tamaño."""
        height, width = image.shape[:2]
        self._net.setInputSize((width, height))
        _, faces = self._net.detect(image)
        if faces is None:
            return []
        detections = [self._to_detection(row, width, height) for row in faces]
        valid = [d for d in detections if min(d.box[2], d.box[3]) >= self._min_face_size]
        return sorted(valid, key=lambda d: d.area, reverse=True)

    @staticmethod
    def _to_detection(row: np.ndarray, width: int, height: int) -> FaceDetection:
        x, y, w, h = (int(round(v)) for v in row[:4])
        x, y = max(x, 0), max(y, 0)
        w, h = min(w, width - x), min(h, height - y)
        points = tuple((int(row[i]), int(row[i + 1])) for i in range(4, 14, 2))
        return FaceDetection(
            box=(x, y, w, h),
            score=float(row[14]),
            landmarks=points,
            raw=row.copy(),
        )


def crop(image: np.ndarray, box: tuple, margin: float = 0.15) -> np.ndarray:
    """Recorta el rostro con un margen proporcional, sin salir de la imagen."""
    x, y, w, h = box
    pad_x, pad_y = int(w * margin), int(h * margin)
    height, width = image.shape[:2]
    x0, y0 = max(x - pad_x, 0), max(y - pad_y, 0)
    x1, y1 = min(x + w + pad_x, width), min(y + h + pad_y, height)
    return image[y0:y1, x0:x1].copy()
