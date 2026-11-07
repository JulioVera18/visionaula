"""Dibujo de resultados directamente sobre el fotograma con OpenCV."""

import cv2
import numpy as np

FONT = cv2.FONT_HERSHEY_SIMPLEX

COLOR_KNOWN = (80, 200, 60)       # verde (BGR)
COLOR_CONFIRMED = (255, 170, 30)  # azul
COLOR_UNKNOWN = (40, 60, 230)     # rojo
COLOR_LANDMARK = (0, 220, 255)    # amarillo
COLOR_TEXT = (255, 255, 255)


def _ascii(text: str) -> str:
    """cv2.putText solo admite ASCII: se reemplazan tildes y eñes."""
    table = str.maketrans("áéíóúÁÉÍÓÚñÑüÜ", "aeiouAEIOUnNuU")
    return text.translate(table).encode("ascii", "replace").decode("ascii")


def draw_label(image: np.ndarray, text: str, origin: tuple, color: tuple) -> None:
    text = _ascii(text)
    scale, thickness = 0.55, 1
    (tw, th), baseline = cv2.getTextSize(text, FONT, scale, thickness)
    x, y = origin
    y = max(y, th + baseline + 4)
    cv2.rectangle(image, (x, y - th - baseline - 6), (x + tw + 8, y), color, cv2.FILLED)
    cv2.putText(image, text, (x + 4, y - baseline - 2), FONT, scale, COLOR_TEXT, thickness, cv2.LINE_AA)


def draw_corners(image: np.ndarray, box: tuple, color: tuple, thickness: int = 2) -> None:
    """Marco con esquinas resaltadas (estilo visor)."""
    x, y, w, h = box
    length = max(int(min(w, h) * 0.22), 8)
    cv2.rectangle(image, (x, y), (x + w, y + h), color, 1, cv2.LINE_AA)
    for cx, cy, dx, dy in ((x, y, 1, 1), (x + w, y, -1, 1), (x, y + h, 1, -1), (x + w, y + h, -1, -1)):
        cv2.line(image, (cx, cy), (cx + dx * length, cy), color, thickness + 1, cv2.LINE_AA)
        cv2.line(image, (cx, cy), (cx, cy + dy * length), color, thickness + 1, cv2.LINE_AA)


def draw_landmarks(image: np.ndarray, landmarks: tuple) -> None:
    for point in landmarks:
        cv2.circle(image, tuple(point), 2, COLOR_LANDMARK, cv2.FILLED, cv2.LINE_AA)


def pixelate(image: np.ndarray, box: tuple, blocks: int = 10) -> None:
    """Pixela una región (modo privacidad para rostros desconocidos)."""
    x, y, w, h = box
    region = image[y:y + h, x:x + w]
    if region.size == 0:
        return
    small = cv2.resize(region, (blocks, blocks), interpolation=cv2.INTER_LINEAR)
    image[y:y + h, x:x + w] = cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)


def draw_hud(image: np.ndarray, lines: list) -> None:
    """Panel semitransparente con información del procesamiento."""
    if not lines:
        return
    height = 22 * len(lines) + 10
    width = max(cv2.getTextSize(_ascii(t), FONT, 0.5, 1)[0][0] for t in lines) + 20
    overlay = image.copy()
    cv2.rectangle(overlay, (8, 8), (8 + width, 8 + height), (20, 20, 20), cv2.FILLED)
    cv2.addWeighted(overlay, 0.55, image, 0.45, 0, dst=image)
    for index, text in enumerate(lines):
        position = (18, 30 + index * 22)
        cv2.putText(image, _ascii(text), position, FONT, 0.5, COLOR_TEXT, 1, cv2.LINE_AA)
