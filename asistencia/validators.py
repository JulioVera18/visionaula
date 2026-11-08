"""Validación de la cédula de identidad ecuatoriana.

Reglas del Registro Civil del Ecuador:
1. Exactamente 10 dígitos.
2. Los dos primeros dígitos son el código de provincia: 01 a 24, o 30
   (ecuatorianos registrados en el exterior).
3. El tercer dígito es menor que 6 (persona natural).
4. El décimo dígito es el verificador, calculado con el algoritmo módulo 10:
   los 9 primeros dígitos se multiplican alternadamente por 2 y 1; si un
   producto es mayor que 9 se le resta 9; se suman los resultados y el
   verificador es lo que falta para llegar a la siguiente decena.
"""

import re

from django.core.exceptions import ValidationError

LONGITUD_CEDULA = 10
PROVINCIAS_VALIDAS = frozenset(range(1, 25)) | {30}
TERCER_DIGITO_MAXIMO = 5
COEFICIENTES = (2, 1, 2, 1, 2, 1, 2, 1, 2)


def normalizar_cedula(valor: str) -> str:
    """Quita espacios y guiones que el usuario suele escribir (091234567-5)."""
    return re.sub(r"[\s-]", "", valor or "")


def digito_verificador(primeros_nueve: str) -> int:
    total = 0
    for digito, coeficiente in zip(primeros_nueve, COEFICIENTES, strict=True):
        producto = int(digito) * coeficiente
        total += producto - 9 if producto > 9 else producto
    return (10 - total % 10) % 10


def es_cedula_valida(valor: str) -> bool:
    try:
        validar_cedula_ecuatoriana(valor)
    except ValidationError:
        return False
    return True


def validar_cedula_ecuatoriana(valor: str) -> None:
    """Lanza ValidationError con un mensaje claro si la cédula no es válida."""
    cedula = normalizar_cedula(valor)
    if not re.fullmatch(rf"[0-9]{{{LONGITUD_CEDULA}}}", cedula):
        raise ValidationError(
            "La cédula debe tener exactamente 10 dígitos numéricos.", code="longitud"
        )
    if int(cedula[:2]) not in PROVINCIAS_VALIDAS:
        raise ValidationError(
            "Los dos primeros dígitos no corresponden a una provincia del Ecuador (01-24 o 30).",
            code="provincia",
        )
    if int(cedula[2]) > TERCER_DIGITO_MAXIMO:
        raise ValidationError(
            "El tercer dígito debe ser menor que 6 (cédula de persona natural).",
            code="tercer_digito",
        )
    if digito_verificador(cedula[:9]) != int(cedula[9]):
        raise ValidationError(
            "La cédula no es válida: el dígito verificador no coincide.", code="verificador"
        )
