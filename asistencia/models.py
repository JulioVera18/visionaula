"""Modelos de datos (persistidos en PostgreSQL)."""

from datetime import datetime
from datetime import timezone as dt_timezone

from django.conf import settings
from django.db import models
from django.db.models.functions import Coalesce
from django.utils import timezone

from vision.recognizer import from_bytes

from .validators import LONGITUD_CEDULA, validar_cedula_ecuatoriana

EPOCH = datetime(1970, 1, 1, tzinfo=dt_timezone.utc)


class Estudiante(models.Model):
    cedula = models.CharField(
        "cédula",
        max_length=LONGITUD_CEDULA,
        unique=True,
        validators=[validar_cedula_ecuatoriana],
        error_messages={"unique": "Ya existe un estudiante registrado con esta cédula."},
    )
    nombres = models.CharField(max_length=80)
    apellidos = models.CharField(max_length=80)
    email = models.EmailField("correo", blank=True)
    curso = models.CharField("curso / paralelo", max_length=60, blank=True)
    activo = models.BooleanField(default=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["apellidos", "nombres"]

    def __str__(self) -> str:
        return f"{self.apellidos} {self.nombres} ({self.cedula})"

    @property
    def nombre_completo(self) -> str:
        return f"{self.nombres} {self.apellidos}"

    @property
    def nombre_corto(self) -> str:
        return f"{self.nombres.split()[0]} {self.apellidos.split()[0]}"


class MuestraRostro(models.Model):
    """Embedding SFace (128 floats) de una foto del estudiante."""

    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE, related_name="muestras")
    embedding = models.BinaryField()
    imagen = models.ImageField(upload_to="rostros/%Y/%m/")
    calidad = models.FloatField(default=0)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado"]
        verbose_name = "muestra de rostro"
        verbose_name_plural = "muestras de rostro"

    def vector(self):
        return from_bytes(self.embedding)


class SesionClase(models.Model):
    asignatura = models.CharField(max_length=100)
    tema = models.CharField(max_length=150, blank=True)
    docente = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="sesiones"
    )
    inicio = models.DateTimeField(default=timezone.now)
    fin = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-inicio"]
        constraints = [
            # Índice único parcial: todas las sesiones abiertas (fin NULL) producen el
            # mismo valor, así que la BD solo admite una a la vez (PostgreSQL y SQLite).
            models.UniqueConstraint(
                Coalesce("fin", models.Value(EPOCH)),
                condition=models.Q(fin__isnull=True),
                name="una_sesion_activa",
            )
        ]
        verbose_name = "sesión de clase"
        verbose_name_plural = "sesiones de clase"

    def __str__(self) -> str:
        return f"{self.asignatura} - {timezone.localtime(self.inicio):%d/%m/%Y %H:%M}"

    @property
    def activa(self) -> bool:
        return self.fin is None

    def cerrar(self) -> None:
        if self.fin is None:
            self.fin = timezone.now()
            self.save(update_fields=["fin"])


class Asistencia(models.Model):
    sesion = models.ForeignKey(SesionClase, on_delete=models.CASCADE, related_name="asistencias")
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE, related_name="asistencias")
    registrado = models.DateTimeField(default=timezone.now)
    similitud = models.FloatField()
    evidencia = models.ImageField(upload_to="evidencias/%Y/%m/", blank=True)

    class Meta:
        ordering = ["registrado"]
        constraints = [
            models.UniqueConstraint(
                fields=["sesion", "estudiante"], name="asistencia_unica_por_sesion"
            )
        ]

    def __str__(self) -> str:
        return f"{self.estudiante} @ {self.sesion}"
