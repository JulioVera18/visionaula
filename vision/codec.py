"""Conversión entre bytes (JPEG/PNG) y matrices de OpenCV."""

import base64

import cv2
import numpy as np

MAX_IMAGE_BYTES = 4 * 1024 * 1024  # 4 MB por fotograma
MAX_IMAGE_SIDE = 4096


class InvalidImageError(ValueError):
    """La imagen recibida está vacía, es demasiado grande o no es decodificable."""


def decode_image(data: bytes) -> np.ndarray:
    """Decodifica bytes de imagen a una matriz BGR de OpenCV."""
    if not data:
        raise InvalidImageError("La imagen está vacía.")
    if len(data) > MAX_IMAGE_BYTES:
        raise InvalidImageError("La imagen supera el tamaño máximo permitido (4 MB).")
    buffer = np.frombuffer(data, dtype=np.uint8)
    image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
    if image is None:
        raise InvalidImageError("El archivo no es una imagen válida.")
    height, width = image.shape[:2]
    if max(height, width) > MAX_IMAGE_SIDE:
        raise InvalidImageError("La resolución de la imagen es demasiado alta.")
    return image


def encode_jpeg(image: np.ndarray, quality: int = 80) -> bytes:
    """Codifica una matriz BGR como JPEG."""
    ok, buffer = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, int(quality)])
    if not ok:
        raise InvalidImageError("No se pudo codificar la imagen.")
    return buffer.tobytes()


def to_data_url(image: np.ndarray, quality: int = 80) -> str:
    """Devuelve la imagen como data URL lista para un <img> del navegador."""
    encoded = base64.b64encode(encode_jpeg(image, quality)).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"
