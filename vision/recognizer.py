"""Reconocimiento facial con SFace (cv2.FaceRecognizerSF).

Cada rostro se alinea con sus 5 puntos faciales y se convierte en un vector
(embedding) de 128 dimensiones normalizado. Dos rostros pertenecen a la misma
persona cuando la similitud coseno entre sus vectores supera un umbral.
"""

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from .detector import FaceDetection

EMBEDDING_SIZE = 128
DEFAULT_THRESHOLD = 0.40  # OpenCV recomienda 0.363 para SFace; usamos uno más estricto


@dataclass(frozen=True)
class Gallery:
    """Galería inmutable de embeddings conocidos (una fila por muestra)."""

    labels: tuple
    matrix: np.ndarray

    @property
    def is_empty(self) -> bool:
        return len(self.labels) == 0


@dataclass(frozen=True)
class Match:
    label: object  # id del estudiante o None si es desconocido
    similarity: float

    @property
    def is_known(self) -> bool:
        return self.label is not None


EMPTY_GALLERY = Gallery(labels=(), matrix=np.zeros((0, EMBEDDING_SIZE), dtype=np.float32))


def normalize(vector: np.ndarray) -> np.ndarray:
    flat = np.asarray(vector, dtype=np.float32).reshape(-1)
    norm = float(np.linalg.norm(flat))
    return flat / norm if norm > 0 else flat


def build_gallery(pairs) -> Gallery:
    """Construye la galería a partir de pares (etiqueta, embedding)."""
    items = [(label, normalize(vector)) for label, vector in pairs]
    if not items:
        return EMPTY_GALLERY
    labels = tuple(label for label, _ in items)
    matrix = np.vstack([vector for _, vector in items]).astype(np.float32)
    return Gallery(labels=labels, matrix=matrix)


def match(gallery: Gallery, embedding: np.ndarray, threshold: float = DEFAULT_THRESHOLD) -> Match:
    """Busca la muestra más parecida. Como los vectores están normalizados,
    el producto punto equivale a la similitud coseno."""
    if gallery.is_empty:
        return Match(label=None, similarity=0.0)
    similarities = gallery.matrix @ normalize(embedding)
    best = int(np.argmax(similarities))
    score = float(similarities[best])
    label = gallery.labels[best] if score >= threshold else None
    return Match(label=label, similarity=round(score, 4))


class FaceEmbedder:
    def __init__(self, model_path: Path):
        self._net = cv2.FaceRecognizerSF.create(str(model_path), "")

    def align(self, image: np.ndarray, detection: FaceDetection) -> np.ndarray:
        """Devuelve el rostro alineado y recortado a 112x112 píxeles."""
        return self._net.alignCrop(image, detection.raw.reshape(1, -1))

    def embed_aligned(self, aligned: np.ndarray) -> np.ndarray:
        return normalize(self._net.feature(aligned))

    def embed(self, image: np.ndarray, detection: FaceDetection) -> np.ndarray:
        return self.embed_aligned(self.align(image, detection))


def to_bytes(embedding: np.ndarray) -> bytes:
    return normalize(embedding).astype(np.float32).tobytes()


def from_bytes(data: bytes) -> np.ndarray:
    vector = np.frombuffer(bytes(data), dtype=np.float32)
    if vector.size != EMBEDDING_SIZE:
        raise ValueError("Embedding con dimensión inválida.")
    return vector
