from django import forms

from .models import Estudiante, SesionClase
from .validators import normalizar_cedula


class EstudianteForm(forms.ModelForm):
    # Se aceptan hasta 13 caracteres para permitir "091234567-5" o espacios;
    # clean_cedula los quita y el modelo valida la cédula ecuatoriana.
    cedula = forms.CharField(
        label="Cédula",
        max_length=13,
        help_text="Cédula de identidad ecuatoriana de 10 dígitos.",
        widget=forms.TextInput(
            attrs={
                "placeholder": "0912345675",
                "autofocus": True,
                "inputmode": "numeric",
                "autocomplete": "off",
            }
        ),
    )

    class Meta:
        model = Estudiante
        fields = ["cedula", "nombres", "apellidos", "email", "curso", "activo"]
        widgets = {
            "nombres": forms.TextInput(attrs={"placeholder": "Ana María"}),
            "apellidos": forms.TextInput(attrs={"placeholder": "Pérez López"}),
            "email": forms.EmailInput(attrs={"placeholder": "ana.perez@unemi.edu.ec"}),
            "curso": forms.TextInput(attrs={"placeholder": "Software - 5to A"}),
        }

    def clean_cedula(self) -> str:
        return normalizar_cedula(self.cleaned_data["cedula"])

    def clean_nombres(self) -> str:
        return " ".join(self.cleaned_data["nombres"].split()).title()

    def clean_apellidos(self) -> str:
        return " ".join(self.cleaned_data["apellidos"].split()).title()


class SesionForm(forms.ModelForm):
    class Meta:
        model = SesionClase
        fields = ["asignatura", "tema"]
        widgets = {
            "asignatura": forms.TextInput(attrs={"placeholder": "Construcción de Software"}),
            "tema": forms.TextInput(attrs={"placeholder": "Práctica 3 - OpenCV"}),
        }
