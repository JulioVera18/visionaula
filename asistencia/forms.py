from django import forms

from .models import Estudiante, SesionClase


class EstudianteForm(forms.ModelForm):
    class Meta:
        model = Estudiante
        fields = ["codigo", "nombres", "apellidos", "email", "curso", "activo"]
        widgets = {
            "codigo": forms.TextInput(attrs={"placeholder": "0912345678", "autofocus": True}),
            "nombres": forms.TextInput(attrs={"placeholder": "Ana María"}),
            "apellidos": forms.TextInput(attrs={"placeholder": "Pérez López"}),
            "email": forms.EmailInput(attrs={"placeholder": "ana.perez@unemi.edu.ec"}),
            "curso": forms.TextInput(attrs={"placeholder": "Software - 5to A"}),
        }

    def clean_codigo(self) -> str:
        return self.cleaned_data["codigo"].strip().upper()

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
