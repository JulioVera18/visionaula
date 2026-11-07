from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from vision.model_store import MODELS, ModelUnavailableError, download_model, is_model_valid


class Command(BaseCommand):
    help = "Descarga y verifica (SHA-256) los modelos ONNX de OpenCV Zoo: YuNet y SFace."

    def add_arguments(self, parser):
        parser.add_argument(
            "--forzar", action="store_true", help="Volver a descargar aunque existan."
        )

    def handle(self, *args, **options):
        models_dir = settings.VISION["MODELS_DIR"]
        for key, spec in MODELS.items():
            if not options["forzar"] and is_model_valid(models_dir, key):
                self.stdout.write(self.style.SUCCESS(f"[OK] {spec.filename} ya está instalado."))
                continue
            self.stdout.write(f"Descargando {spec.description}...")
            try:
                path = download_model(models_dir, key)
            except ModelUnavailableError as exc:
                raise CommandError(str(exc)) from exc
            self.stdout.write(self.style.SUCCESS(f"[OK] {path}"))
        self.stdout.write(self.style.SUCCESS("Modelos listos."))
