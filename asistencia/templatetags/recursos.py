"""Import map que agrega una versión a cada módulo JavaScript.

Los módulos se importan entre sí con rutas relativas (./camara.js) y el navegador
los guarda en caché. Si el código cambia, el navegador podría combinar un HTML
nuevo con un JavaScript viejo. El import map redirige cada módulo a su URL con
?v=<hash del contenido>, así cualquier cambio obliga a descargar la versión nueva.
"""

import hashlib
import json

from django import template
from django.contrib.staticfiles import finders
from django.templatetags.static import static
from django.utils.html import format_html
from django.utils.safestring import mark_safe

register = template.Library()

MODULOS_JS = (
    "asistencia/js/camara.js",
    "asistencia/js/enrolar.js",
    "asistencia/js/monitor.js",
    "asistencia/js/overlay.js",
)
LONGITUD_VERSION = 10


def _version(ruta: str) -> str | None:
    archivo = finders.find(ruta)
    if not archivo:
        return None
    with open(archivo, "rb") as contenido:
        return hashlib.sha256(contenido.read()).hexdigest()[:LONGITUD_VERSION]


@register.simple_tag
def mapa_modulos_js():
    imports = {}
    for ruta in MODULOS_JS:
        version = _version(ruta)
        if version:
            url = static(ruta)
            imports[url] = f"{url}?v={version}"
    contenido = json.dumps({"imports": imports}).replace("</", r"<\/")
    return format_html('<script type="importmap">{}</script>', mark_safe(contenido))


@register.simple_tag
def estatico_versionado(ruta: str) -> str:
    """URL de un archivo estático con ?v=<hash> (p. ej. la hoja de estilos)."""
    version = _version(ruta)
    return f"{static(ruta)}?v={version}" if version else static(ruta)
