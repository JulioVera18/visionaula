"""Lógica de negocio: une el módulo de visión con la base de datos."""

import logging
import threading
from dataclasses import dataclass

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.db.models import Count, Max

from vision import codec
from vision.model_store import require_model
from vision.pipeline import EnrollmentError, FaceEngine, RenderOptions, render
from vision.recognizer import build_gallery, to_bytes

from .models import Asistencia, Estudiante, MuestraRostro, SesionClase
from .signals import gallery_version
from .tracker import ConfirmationTracker

logger = logging.getLogger(__name__)


class SampleLimitError(EnrollmentError):
    """El estudiante alcanzó el máximo de muestras permitidas."""


# ---------------------------------------------------------------------------
# Motor de visión (se crea una sola vez por proceso)
# ---------------------------------------------------------------------------


class _Singleton:
    """Crea el objeto una sola vez aunque varios hilos lo pidan a la vez
    (doble verificación con candado; lru_cache no lo garantiza)."""

    def __init__(self, factory):
        self._factory = factory
        self._lock = threading.Lock()
        self._instance = None

    def __call__(self):
        if self._instance is None:
            with self._lock:
                if self._instance is None:
                    self._instance = self._factory()
        return self._instance

    def reset(self) -> None:
        with self._lock:
            self._instance = None


def _crear_engine() -> FaceEngine:
    cfg = settings.VISION
    return FaceEngine.from_models(
        yunet=require_model(cfg["MODELS_DIR"], "yunet"),
        sface=require_model(cfg["MODELS_DIR"], "sface"),
        score_threshold=cfg["DETECTION_SCORE"],
        min_face_size=cfg["MIN_FACE_SIZE"],
    )


def _crear_tracker() -> ConfirmationTracker:
    cfg = settings.VISION
    return ConfirmationTracker(cfg["CONFIRM_FRAMES"], cfg["CONFIRM_WINDOW_SECONDS"])


get_engine = _Singleton(_crear_engine)
get_tracker = _Singleton(_crear_tracker)


# ---------------------------------------------------------------------------
# Galería de rostros con caché invalidada por cambios en la BD
# ---------------------------------------------------------------------------


class GalleryCache:
    def __init__(self):
        self._lock = threading.Lock()
        self._signature = None
        self._gallery = build_gallery([])
        self._names: dict = {}

    @staticmethod
    def _queryset():
        return MuestraRostro.objects.filter(estudiante__activo=True)

    def _current_signature(self) -> tuple:
        # La versión cambia con cualquier guardado/borrado en este proceso (señales);
        # los agregados cubren cambios hechos desde otro proceso (p. ej. el admin).
        stats = self._queryset().aggregate(total=Count("id"), ultimo=Max("id"))
        activos = list(Estudiante.objects.filter(activo=True).values_list("id", flat=True))
        return (gallery_version(), stats["total"], stats["ultimo"], hash(tuple(sorted(activos))))

    def get(self) -> tuple:
        """Devuelve (galería, nombres) recargando solo si la BD cambió."""
        signature = self._current_signature()
        with self._lock:
            if signature != self._signature:
                rows = self._queryset().select_related("estudiante")
                self._gallery = build_gallery((m.estudiante_id, m.vector()) for m in rows)
                self._names = {m.estudiante_id: m.estudiante.nombre_corto for m in rows}
                self._signature = signature
                logger.info("Galería recargada: %s muestras", len(self._gallery.labels))
            return self._gallery, dict(self._names)


gallery_cache = GalleryCache()


# ---------------------------------------------------------------------------
# Registro de muestras (enrolamiento)
# ---------------------------------------------------------------------------


def registrar_muestra(estudiante: Estudiante, image_bytes: bytes) -> MuestraRostro:
    limit = settings.VISION["MAX_SAMPLES_PER_STUDENT"]
    if estudiante.muestras.count() >= limit:
        raise SampleLimitError(f"Se alcanzó el máximo de {limit} muestras.")
    image = codec.decode_image(image_bytes)
    sample = get_engine().enrollment_sample(image)
    muestra = MuestraRostro(
        estudiante=estudiante,
        embedding=to_bytes(sample.embedding),
        calidad=sample.quality.score,
    )
    filename = f"{estudiante.codigo}.jpg"
    muestra.imagen.save(filename, ContentFile(codec.encode_jpeg(sample.face_crop, 90)), save=False)
    muestra.save()
    return muestra


# ---------------------------------------------------------------------------
# Procesamiento de fotogramas en vivo
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FrameRequest:
    image_bytes: bytes
    sesion: SesionClase | None
    view_mode: str = "normal"
    privacy: bool = False
    # False: solo se devuelven los datos de los rostros y el navegador los dibuja
    # sobre el video en vivo (mucho más fluido). True: se devuelve el fotograma
    # procesado por OpenCV (necesario para filtros y modo privacidad).
    with_image: bool = True


def _confirmados(sesion: SesionClase | None) -> set:
    if sesion is None:
        return set()
    return set(sesion.asistencias.values_list("estudiante_id", flat=True))


def _registrar_asistencia(sesion: SesionClase, face) -> Asistencia | None:
    asistencia = Asistencia(
        sesion=sesion, estudiante_id=face.match.label, similitud=face.match.similarity
    )
    evidencia = ContentFile(codec.encode_jpeg(face.face_crop, 85))
    asistencia.evidencia.save(f"s{sesion.pk}_e{face.match.label}.jpg", evidencia, save=False)
    try:
        with transaction.atomic():
            asistencia.save()
    except IntegrityError:
        asistencia.evidencia.delete(save=False)
        return None
    logger.info("Asistencia registrada: estudiante=%s sesion=%s", face.match.label, sesion.pk)
    return asistencia


def _actualizar_asistencias(sesion, analysis, confirmados: set) -> list:
    if sesion is None or not sesion.activa:
        return []
    tracker = get_tracker()
    nuevas = []
    for face in analysis.known:
        label = face.match.label
        if label in confirmados:
            continue
        if tracker.observe(sesion.pk, label):
            asistencia = _registrar_asistencia(sesion, face)
            if asistencia is not None:
                nuevas.append(asistencia)
                confirmados.add(label)
    return nuevas


def _face_payload(face, names: dict, confirmados: set, sesion) -> dict:
    label = face.match.label
    progress = get_tracker().progress(sesion.pk, label) if (sesion and label) else 0.0
    return {
        "box": list(face.box),
        "puntos": [list(point) for point in face.landmarks],
        "estudiante_id": label,
        "nombre": names.get(label) if label else None,
        "similitud": face.match.similarity,
        "confirmado": label in confirmados,
        "progreso": 1.0 if label in confirmados else round(progress, 2),
    }


def _asistencia_payload(asistencia: Asistencia) -> dict:
    estudiante = asistencia.estudiante
    return {
        "id": asistencia.pk,
        "estudiante": estudiante.nombre_completo,
        "codigo": estudiante.codigo,
        "similitud": asistencia.similitud,
        "hora": asistencia.registrado.isoformat(),
        "evidencia": asistencia.evidencia.url if asistencia.evidencia else "",
    }


def procesar_frame(request: FrameRequest) -> dict:
    """Pipeline completo de un fotograma; devuelve el payload JSON."""
    image = codec.decode_image(request.image_bytes)
    gallery, names = gallery_cache.get()
    analysis = get_engine().analyze(image, gallery, settings.VISION["MATCH_THRESHOLD"])
    confirmados = _confirmados(request.sesion)
    nuevas = _actualizar_asistencias(request.sesion, analysis, confirmados)
    imagen = None
    if request.with_image:
        options = RenderOptions(
            view_mode=request.view_mode,
            privacy=request.privacy,
            confirmed_labels=frozenset(confirmados),
        )
        imagen = codec.to_data_url(render(analysis, names, options), 85)
    alto, ancho = analysis.image.shape[:2]
    return {
        "imagen": imagen,
        "ancho": ancho,
        "alto": alto,
        "rostros": [_face_payload(f, names, confirmados, request.sesion) for f in analysis.faces],
        "total_rostros": len(analysis.faces),
        "desconocidos": analysis.unknown_count,
        "poca_luz": analysis.low_light,
        "ms": analysis.elapsed_ms,
        "nuevas_asistencias": [_asistencia_payload(a) for a in nuevas],
        "galeria_vacia": gallery.is_empty,
    }


class SesionActivaError(Exception):
    """Ya existe una sesión de clase abierta."""


def abrir_sesion(sesion: SesionClase) -> SesionClase:
    """Guarda la sesión; la restricción única parcial de la BD impide dos activas
    incluso ante envíos simultáneos."""
    try:
        with transaction.atomic():
            sesion.save()
    except IntegrityError as exc:
        raise SesionActivaError(
            "Ya existe una sesión activa: ciérrela antes de abrir otra."
        ) from exc
    return sesion


def cerrar_sesion(sesion: SesionClase) -> None:
    sesion.cerrar()
    get_tracker().forget_session(sesion.pk)


def estadisticas_sesion(sesion: SesionClase) -> dict:
    inscritos = Estudiante.objects.filter(activo=True).count()
    presentes = sesion.asistencias.count()
    porcentaje = round(presentes * 100 / inscritos, 1) if inscritos else 0.0
    return {
        "inscritos": inscritos,
        "presentes": presentes,
        "ausentes": max(inscritos - presentes, 0),
        "porcentaje": porcentaje,
    }
