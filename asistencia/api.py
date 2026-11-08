"""Endpoints JSON consumidos por el JavaScript de la cámara.

Formato de respuesta uniforme: {"ok": bool, "data": {...} | null, "error": str | null}
"""

import logging
from functools import wraps

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from vision.codec import InvalidImageError
from vision.model_store import ModelUnavailableError
from vision.pipeline import EnrollmentError
from vision.preprocessing import VIEW_FILTERS

from . import services
from .models import Estudiante, SesionClase

logger = logging.getLogger(__name__)


def json_ok(data: dict, status: int = 200) -> JsonResponse:
    return JsonResponse({"ok": True, "data": data, "error": None}, status=status)


def json_error(message: str, status: int) -> JsonResponse:
    return JsonResponse({"ok": False, "data": None, "error": message}, status=status)


def api_view(func):
    """Exige sesión iniciada y traduce excepciones conocidas a respuestas JSON."""

    @wraps(func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return json_error("Sesión expirada: vuelva a iniciar sesión.", 401)
        try:
            return func(request, *args, **kwargs)
        except InvalidImageError as exc:
            return json_error(str(exc), 400)
        except EnrollmentError as exc:
            return json_error(str(exc), 422)
        except ModelUnavailableError as exc:
            logger.error("Modelo no disponible: %s", exc)
            return json_error(str(exc), 503)
        except Exception:  # noqa: BLE001 - se registra y se responde sin filtrar detalles
            logger.exception("Error inesperado en %s", func.__name__)
            return json_error("Error interno al procesar la imagen.", 500)

    return wrapper


def _leer_frame(request) -> bytes:
    archivo = request.FILES.get("frame")
    if archivo is None:
        raise InvalidImageError("No se recibió el fotograma ('frame').")
    return archivo.read()


def _sesion_desde(request) -> SesionClase | None:
    raw = request.POST.get("sesion", "").strip()
    if not raw:
        return None
    if not raw.isdigit():
        raise InvalidImageError("Identificador de sesión inválido.")
    return SesionClase.objects.filter(pk=int(raw)).first()


@require_POST
@api_view
def procesar_frame(request):
    view_mode = request.POST.get("modo", "normal")
    if view_mode not in VIEW_FILTERS:
        view_mode = "normal"
    frame_request = services.FrameRequest(
        image_bytes=_leer_frame(request),
        sesion=_sesion_desde(request),
        view_mode=view_mode,
        with_image=request.POST.get("imagen", "1") != "0",
    )
    return json_ok(services.procesar_frame(frame_request))


@require_POST
@api_view
def registrar_muestra(request, pk: int):
    estudiante = get_object_or_404(Estudiante, pk=pk)
    muestra = services.registrar_muestra(estudiante, _leer_frame(request))
    return json_ok(
        {
            "id": muestra.pk,
            "imagen": muestra.imagen.url,
            "calidad": muestra.calidad,
            "total": estudiante.muestras.count(),
        },
        status=201,
    )
