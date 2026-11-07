"""Procesamiento de imagen con OpenCV.

Incluye:
- Mejora automática de iluminación (CLAHE sobre el canal L del espacio LAB).
- Métricas de calidad de rostro (nitidez por varianza del Laplaciano y brillo).
- Filtros de visualización seleccionables desde la interfaz web.
"""

from dataclasses import dataclass

import cv2
import numpy as np

LOW_LIGHT_THRESHOLD = 80.0  # brillo medio (0-255) por debajo del cual se corrige
MIN_SHARPNESS = 25.0  # varianza del Laplaciano mínima para un rostro nítido
MIN_FACE_BRIGHTNESS = 45.0
MAX_FACE_BRIGHTNESS = 225.0

_CLAHE = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))


@dataclass(frozen=True)
class FaceQuality:
    sharpness: float
    brightness: float
    ok: bool
    reason: str = ""

    @property
    def score(self) -> float:
        """Puntaje 0-1 combinado, útil para ordenar muestras."""
        sharp = min(self.sharpness / (MIN_SHARPNESS * 4), 1.0)
        light = 1.0 - abs(self.brightness - 128.0) / 128.0
        return round(0.6 * sharp + 0.4 * max(light, 0.0), 3)


def mean_brightness(image: np.ndarray) -> float:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    return float(gray.mean())


def sharpness(image: np.ndarray) -> float:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def enhance_lighting(image: np.ndarray) -> np.ndarray:
    """Ecualiza el contraste local sin alterar los colores (CLAHE en LAB)."""
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    lightness, a_channel, b_channel = cv2.split(lab)
    merged = cv2.merge((_CLAHE.apply(lightness), a_channel, b_channel))
    return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)


def is_low_light(image: np.ndarray, threshold: float = LOW_LIGHT_THRESHOLD) -> bool:
    return mean_brightness(image) < threshold


def resize_max_side(image: np.ndarray, max_side: int) -> np.ndarray:
    """Reduce la imagen si su lado mayor excede max_side (mejora el rendimiento)."""
    height, width = image.shape[:2]
    largest = max(height, width)
    if largest <= max_side:
        return image
    factor = max_side / float(largest)
    size = (int(width * factor), int(height * factor))
    return cv2.resize(image, size, interpolation=cv2.INTER_AREA)


def assess_face_quality(face: np.ndarray) -> FaceQuality:
    """Evalúa si un recorte de rostro es apto para registrarse como muestra."""
    if face is None or face.size == 0:
        return FaceQuality(0.0, 0.0, False, "Rostro vacío.")
    sharp = sharpness(face)
    light = mean_brightness(face)
    if sharp < MIN_SHARPNESS:
        return FaceQuality(sharp, light, False, "Imagen borrosa: mantén la cabeza quieta.")
    if light < MIN_FACE_BRIGHTNESS:
        return FaceQuality(sharp, light, False, "Rostro muy oscuro: mejora la iluminación.")
    if light > MAX_FACE_BRIGHTNESS:
        return FaceQuality(sharp, light, False, "Rostro sobreexpuesto: evita la luz directa.")
    return FaceQuality(sharp, light, True)


# ---------------------------------------------------------------------------
# Filtros de visualización
# ---------------------------------------------------------------------------


def _filter_normal(image: np.ndarray) -> np.ndarray:
    return image


def _filter_gray(image: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)


def _filter_edges(image: np.ndarray) -> np.ndarray:
    gray = cv2.GaussianBlur(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), (5, 5), 0)
    edges = cv2.Canny(gray, 50, 150)
    return cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)


def _filter_thermal(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return cv2.applyColorMap(gray, cv2.COLORMAP_INFERNO)


VIEW_FILTERS = {
    "normal": ("Normal", _filter_normal),
    "clahe": ("Contraste (CLAHE)", enhance_lighting),
    "gris": ("Escala de grises", _filter_gray),
    "bordes": ("Bordes (Canny)", _filter_edges),
    "termico": ("Mapa térmico", _filter_thermal),
}


def apply_view_filter(image: np.ndarray, mode: str) -> np.ndarray:
    """Aplica el filtro elegido; si el modo no existe se devuelve la imagen original."""
    _, func = VIEW_FILTERS.get(mode, VIEW_FILTERS["normal"])
    return func(image)
