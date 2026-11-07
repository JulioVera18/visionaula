"""Señales: invalidan la galería en memoria y borran archivos biométricos huérfanos."""

import threading

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Asistencia, Estudiante, MuestraRostro

_lock = threading.Lock()
_version = 0


def gallery_version() -> int:
    return _version


def _bump(**_kwargs) -> None:
    global _version
    with _lock:
        _version += 1


for _model in (Estudiante, MuestraRostro):
    post_save.connect(_bump, sender=_model, dispatch_uid=f"bump_save_{_model.__name__}")
    post_delete.connect(_bump, sender=_model, dispatch_uid=f"bump_delete_{_model.__name__}")


@receiver(post_delete, sender=MuestraRostro, dispatch_uid="borrar_imagen_muestra")
def borrar_imagen_muestra(sender, instance, **kwargs) -> None:
    if instance.imagen:
        instance.imagen.delete(save=False)


@receiver(post_delete, sender=Asistencia, dispatch_uid="borrar_evidencia_asistencia")
def borrar_evidencia_asistencia(sender, instance, **kwargs) -> None:
    if instance.evidencia:
        instance.evidencia.delete(save=False)
