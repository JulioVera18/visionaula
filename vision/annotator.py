"""Dibujo de resultados directamente sobre el fotograma con OpenCV.

Todas las funciones reciben `scale` para que marcos y textos mantengan el mismo
tamaño visual en 480p, 720p o 1080p (ver ui_scale).
"""

import cv2
import numpy as np

FONT = cv2.FONT_HERSHEY_SIMPLEX
REFERENCE_WIDTH = 960  # ancho para el que se diseñaron los tamaños base

COLOR_KNOWN = (80, 200, 60)  # verde (BGR)
COLOR_CONFIRMED = (255, 170, 30)  # azul
COLOR_UNKNOWN = (40, 60, 230)  # rojo
COLOR_LANDMARK = (0, 220, 255)  # amarillo
COLOR_TEXT = (255, 255, 255)


def ui_scale(image: np.ndarray) -> float:
    """Factor de tamaño de los dibujos según el ancho de la imagen (mínimo 1)."""
    return max(1.0, image.shape[1] / REFERENCE_WIDTH)


def _px(value: float, scale: float) -> int:
    return max(1, int(round(value * scale)))


def _ascii(text: str) -> str:
    """cv2.putText solo admite ASCII: se reemplazan tildes y eñes."""
    table = str.maketrans("áéíóúÁÉÍÓÚñÑüÜ", "aeiouAEIOUnNuU")
    return text.translate(table).encode("ascii", "replace").decode("ascii")


def draw_label(
    image: np.ndarray, text: str, origin: tuple, color: tuple, scale: float = 1.0
) -> None:
    text = _ascii(text)
    font_scale, thickness = 0.55 * scale, _px(1, scale)
    pad = _px(4, scale)
    (tw, th), baseline = cv2.getTextSize(text, FONT, font_scale, thickness)
    x, y = origin
    y = max(y, th + baseline + 2 * pad)
    cv2.rectangle(image, (x, y - th - baseline - 2 * pad), (x + tw + 2 * pad, y), color, cv2.FILLED)
    cv2.putText(
        image,
        text,
        (x + pad, y - baseline - pad // 2),
        FONT,
        font_scale,
        COLOR_TEXT,
        thickness,
        cv2.LINE_AA,
    )


def draw_corners(image: np.ndarray, box: tuple, color: tuple, scale: float = 1.0) -> None:
    """Marco con esquinas resaltadas (estilo visor)."""
    x, y, w, h = box
    length = max(int(min(w, h) * 0.22), 8)
    thickness = _px(3, scale)
    cv2.rectangle(image, (x, y), (x + w, y + h), color, _px(1, scale), cv2.LINE_AA)
    for cx, cy, dx, dy in (
        (x, y, 1, 1),
        (x + w, y, -1, 1),
        (x, y + h, 1, -1),
        (x + w, y + h, -1, -1),
    ):
        cv2.line(image, (cx, cy), (cx + dx * length, cy), color, thickness, cv2.LINE_AA)
        cv2.line(image, (cx, cy), (cx, cy + dy * length), color, thickness, cv2.LINE_AA)


def draw_landmarks(image: np.ndarray, landmarks: tuple, scale: float = 1.0) -> None:
    radius = _px(2, scale)
    for point in landmarks:
        cv2.circle(image, tuple(point), radius, COLOR_LANDMARK, cv2.FILLED, cv2.LINE_AA)


def pixelate(image: np.ndarray, box: tuple, blocks: int = 10) -> None:
    """Pixela una región (privacidad: rostros no registrados)."""
    x, y, w, h = box
    region = image[y : y + h, x : x + w]
    if region.size == 0:
        return
    small = cv2.resize(region, (blocks, blocks), interpolation=cv2.INTER_LINEAR)
    image[y : y + h, x : x + w] = cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)


def draw_hud(image: np.ndarray, lines: list, scale: float = 1.0) -> None:
    """Panel semitransparente con información del procesamiento."""
    if not lines:
        return
    font_scale, thickness = 0.5 * scale, _px(1, scale)
    line_h, margin = _px(22, scale), _px(8, scale)
    width = max(cv2.getTextSize(_ascii(t), FONT, font_scale, thickness)[0][0] for t in lines)
    x1 = min(margin + width + 2 * _px(10, scale), image.shape[1])
    y1 = min(margin + line_h * len(lines) + _px(10, scale), image.shape[0])
    # Solo se mezcla la región del panel (más barato que copiar todo el fotograma 1080p).
    roi = image[margin:y1, margin:x1]
    roi[:] = cv2.addWeighted(roi, 0.45, np.full_like(roi, 20), 0.55, 0)
    for index, text in enumerate(lines):
        position = (margin + _px(10, scale), margin + _px(22, scale) + index * line_h)
        cv2.putText(
            image, _ascii(text), position, FONT, font_scale, COLOR_TEXT, thickness, cv2.LINE_AA
        )
