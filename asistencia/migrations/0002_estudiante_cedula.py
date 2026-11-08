"""El identificador del estudiante pasa a ser la cédula ecuatoriana validada."""

from django.db import migrations, models

import asistencia.validators


class Migration(migrations.Migration):
    dependencies = [
        ("asistencia", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="estudiante",
            old_name="codigo",
            new_name="cedula",
        ),
        migrations.AlterField(
            model_name="estudiante",
            name="cedula",
            field=models.CharField(
                error_messages={"unique": "Ya existe un estudiante registrado con esta cédula."},
                max_length=10,
                unique=True,
                validators=[asistencia.validators.validar_cedula_ecuatoriana],
                verbose_name="cédula",
            ),
        ),
    ]
