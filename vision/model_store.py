"""Descarga y verificación de los modelos ONNX oficiales de OpenCV Zoo.

Los modelos no se guardan en el repositorio (SFace pesa ~37 MB); se descargan
con `python manage.py descargar_modelos` y se verifican con SHA-256.
"""

import hashlib
import shutil
import urllib.request
from dataclasses import dataclass
from pathlib import Path

DOWNLOAD_TIMEOUT_SECONDS = 60
_CHUNK = 1024 * 1024


@dataclass(frozen=True)
class ModelSpec:
    filename: str
    url: str
    sha256: str
    description: str


_ZOO = "https://github.com/opencv/opencv_zoo/raw/main/models"

MODELS = {
    "yunet": ModelSpec(
        filename="face_detection_yunet_2023mar.onnx",
        url=f"{_ZOO}/face_detection_yunet/face_detection_yunet_2023mar.onnx",
        sha256="8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4",
        description="YuNet - detector de rostros (OpenCV Zoo)",
    ),
    "sface": ModelSpec(
        filename="face_recognition_sface_2021dec.onnx",
        url=f"{_ZOO}/face_recognition_sface/face_recognition_sface_2021dec.onnx",
        sha256="0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79",
        description="SFace - reconocimiento facial (OpenCV Zoo)",
    ),
}


class ModelUnavailableError(RuntimeError):
    """El modelo no existe localmente o su descarga/verificación falló."""


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(_CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def model_path(models_dir: Path, key: str) -> Path:
    return Path(models_dir) / MODELS[key].filename


def is_model_valid(models_dir: Path, key: str) -> bool:
    path = model_path(models_dir, key)
    return path.is_file() and sha256_of(path) == MODELS[key].sha256


def require_model(models_dir: Path, key: str) -> Path:
    """Devuelve la ruta del modelo o lanza un error con instrucciones claras."""
    path = model_path(models_dir, key)
    if not path.is_file():
        raise ModelUnavailableError(
            f"Falta el modelo '{MODELS[key].filename}'. "
            "Ejecute: python manage.py descargar_modelos"
        )
    return path


def download_model(models_dir: Path, key: str) -> Path:
    """Descarga el modelo a un archivo temporal, verifica el hash y lo instala."""
    spec = MODELS[key]
    target = model_path(models_dir, key)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".part")
    try:
        with urllib.request.urlopen(spec.url, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:
            with open(temporary, "wb") as handle:
                shutil.copyfileobj(response, handle, _CHUNK)
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        raise ModelUnavailableError(f"No se pudo descargar {spec.filename}: {exc}") from exc
    if sha256_of(temporary) != spec.sha256:
        temporary.unlink(missing_ok=True)
        raise ModelUnavailableError(f"El hash SHA-256 de {spec.filename} no coincide.")
    temporary.replace(target)
    return target
