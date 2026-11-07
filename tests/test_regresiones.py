"""Pruebas de regresión de los hallazgos de la revisión de código."""

import threading
from pathlib import Path

import pytest
from django.db import IntegrityError, transaction
from django.urls import reverse

from asistencia import services
from asistencia.models import Asistencia, Estudiante, SesionClase

from .test_django import frame, nueva_sesion, procesar

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


def test_attendance_retried_after_transient_failure(
        cliente, docente, estudiante, fake_engine, jpeg_bytes, monkeypatch):
    fake_engine.label = estudiante.pk
    sesion = nueva_sesion(docente)
    original = services._registrar_asistencia
    llamadas = {"n": 0}

    def falla_una_vez(sesion_, face):
        llamadas["n"] += 1
        if llamadas["n"] == 1:
            raise OSError("disco lleno")
        return original(sesion_, face)

    monkeypatch.setattr(services, "_registrar_asistencia", falla_una_vez)
    codigos = [procesar(cliente, jpeg_bytes, sesion).status_code for _ in range(4)]
    assert codigos == [200, 200, 500, 200]
    assert Asistencia.objects.filter(estudiante=estudiante).count() == 1


def test_gallery_notices_activation_swap_and_name_change(estudiante, fake_engine, jpeg_bytes):
    otro = Estudiante.objects.create(codigo="X-2", nombres="Luis", apellidos="Mora", activo=False)
    services.registrar_muestra(estudiante, jpeg_bytes)
    services.registrar_muestra(otro, jpeg_bytes)
    cache = services.GalleryCache()
    assert cache.get()[0].labels == (estudiante.pk,)

    Estudiante.objects.filter(pk=estudiante.pk).update(activo=False)  # sin señales
    Estudiante.objects.filter(pk=otro.pk).update(activo=True)
    assert cache.get()[0].labels == (otro.pk,)

    otro.refresh_from_db()
    otro.nombres = "Pedro"
    otro.save()
    assert cache.get()[1][otro.pk] == "Pedro Mora"


def test_deleting_student_removes_biometric_files(cliente, docente, estudiante, fake_engine, jpeg_bytes):
    muestra = services.registrar_muestra(estudiante, jpeg_bytes)
    fake_engine.label = estudiante.pk
    sesion = nueva_sesion(docente)
    for _ in range(3):
        procesar(cliente, jpeg_bytes, sesion)
    evidencia = Path(Asistencia.objects.get().evidencia.path)
    imagen = Path(muestra.imagen.path)
    assert evidencia.exists() and imagen.exists()

    cliente.post(reverse("asistencia:estudiante_eliminar", args=[estudiante.pk]))
    assert not evidencia.exists() and not imagen.exists()


def test_database_allows_only_one_active_session(docente):
    nueva_sesion(docente)
    with pytest.raises(IntegrityError), transaction.atomic():
        nueva_sesion(docente)
    cerrada = SesionClase.objects.get()
    cerrada.cerrar()
    nueva_sesion(docente)  # al cerrar la anterior ya se puede abrir otra
    assert SesionClase.objects.filter(fin__isnull=True).count() == 1


def test_closing_session_forgets_tracker_streaks(cliente, docente):
    sesion = nueva_sesion(docente)
    services.get_tracker().observe(sesion.pk, 99)
    cliente.post(reverse("asistencia:sesion_cerrar", args=[sesion.pk]))
    assert services.get_tracker().progress(sesion.pk, 99) == 0.0


def test_singleton_is_created_once_under_concurrency():
    creados = []
    barrera = threading.Barrier(8)

    def fabrica():
        creados.append(object())
        return creados[-1]

    singleton = services._Singleton(fabrica)

    def pedir():
        barrera.wait()
        singleton()

    hilos = [threading.Thread(target=pedir) for _ in range(8)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join()
    assert len(creados) == 1


def test_frame_helper_is_reusable(jpeg_bytes):
    assert frame(jpeg_bytes).size == len(jpeg_bytes)
