from django.apps import AppConfig


class AsistenciaConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "asistencia"
    verbose_name = "Control de asistencia"

    def ready(self) -> None:
        from . import signals  # noqa: F401  (registra las señales)
