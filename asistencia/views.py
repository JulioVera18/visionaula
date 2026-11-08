"""Vistas HTML de la aplicación."""

import csv

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from vision.model_store import MODELS, model_path
from vision.preprocessing import VIEW_FILTERS

from .forms import EstudianteForm, SesionForm
from .models import Asistencia, Estudiante, MuestraRostro, SesionClase
from .services import SesionActivaError, abrir_sesion, cerrar_sesion, estadisticas_sesion


def _modelos_listos() -> bool:
    models_dir = settings.VISION["MODELS_DIR"]
    return all(model_path(models_dir, key).is_file() for key in MODELS)


@login_required
def dashboard(request):
    hoy = timezone.localdate()
    estudiantes = Estudiante.objects.filter(activo=True)
    contexto = {
        "total_estudiantes": estudiantes.count(),
        "con_rostro": estudiantes.filter(muestras__isnull=False).distinct().count(),
        "total_sesiones": SesionClase.objects.count(),
        "asistencias_hoy": Asistencia.objects.filter(registrado__date=hoy).count(),
        "sesion_activa": SesionClase.objects.filter(fin__isnull=True).first(),
        "ultimas": Asistencia.objects.select_related("estudiante", "sesion").order_by(
            "-registrado"
        )[:8],
        "modelos_listos": _modelos_listos(),
    }
    return render(request, "asistencia/dashboard.html", contexto)


# ---------------------------------------------------------------------------
# Estudiantes
# ---------------------------------------------------------------------------


class EstudianteListView(LoginRequiredMixin, ListView):
    model = Estudiante
    template_name = "asistencia/estudiantes/lista.html"
    context_object_name = "estudiantes"
    paginate_by = 20

    def get_queryset(self):
        queryset = Estudiante.objects.annotate(n_muestras=Count("muestras")).order_by(
            "apellidos", "nombres"
        )
        termino = self.request.GET.get("q", "").strip()
        if termino:
            queryset = queryset.filter(
                Q(nombres__icontains=termino)
                | Q(apellidos__icontains=termino)
                | Q(cedula__icontains=termino)
            )
        return queryset

    def get_context_data(self, **kwargs):
        return super().get_context_data(q=self.request.GET.get("q", ""), **kwargs)


class EstudianteCreateView(LoginRequiredMixin, CreateView):
    model = Estudiante
    form_class = EstudianteForm
    template_name = "asistencia/estudiantes/form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Estudiante creado. Ahora registra su rostro.")
        return response

    def get_success_url(self):
        return reverse_lazy("asistencia:estudiante_enrolar", args=[self.object.pk])


class EstudianteUpdateView(LoginRequiredMixin, UpdateView):
    model = Estudiante
    form_class = EstudianteForm
    template_name = "asistencia/estudiantes/form.html"
    success_url = reverse_lazy("asistencia:estudiantes")

    def form_valid(self, form):
        messages.success(self.request, "Datos del estudiante actualizados.")
        return super().form_valid(form)


@login_required
@require_POST
def estudiante_eliminar(request, pk: int):
    estudiante = get_object_or_404(Estudiante, pk=pk)
    estudiante.delete()  # las señales borran fotos de muestras y evidencias
    messages.success(request, f"Se eliminó a {estudiante.nombre_completo}.")
    return redirect("asistencia:estudiantes")


@login_required
def estudiante_enrolar(request, pk: int):
    estudiante = get_object_or_404(Estudiante, pk=pk)
    contexto = {
        "estudiante": estudiante,
        "muestras": estudiante.muestras.all(),
        "max_muestras": settings.VISION["MAX_SAMPLES_PER_STUDENT"],
        "modelos_listos": _modelos_listos(),
    }
    return render(request, "asistencia/estudiantes/enrolar.html", contexto)


@login_required
@require_POST
def muestra_eliminar(request, pk: int):
    muestra = get_object_or_404(MuestraRostro, pk=pk)
    estudiante_pk = muestra.estudiante_id
    muestra.delete()
    messages.info(request, "Muestra eliminada.")
    return redirect("asistencia:estudiante_enrolar", pk=estudiante_pk)


# ---------------------------------------------------------------------------
# Sesiones de clase
# ---------------------------------------------------------------------------


@login_required
def sesiones(request):
    form = SesionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        sesion = form.save(commit=False)
        sesion.docente = request.user
        try:
            abrir_sesion(sesion)
        except SesionActivaError as exc:
            messages.error(request, str(exc))
            return redirect("asistencia:sesiones")
        messages.success(request, "Sesión iniciada. ¡Abre el monitor para tomar asistencia!")
        return redirect(f"{reverse_lazy('asistencia:monitor')}?sesion={sesion.pk}")
    listado = SesionClase.objects.annotate(presentes=Count("asistencias")).select_related("docente")
    return render(request, "asistencia/sesiones/lista.html", {"form": form, "sesiones": listado})


class SesionDetailView(LoginRequiredMixin, DetailView):
    model = SesionClase
    template_name = "asistencia/sesiones/detalle.html"
    context_object_name = "sesion"

    def get_context_data(self, **kwargs):
        sesion = self.object
        presentes_ids = sesion.asistencias.values_list("estudiante_id", flat=True)
        return super().get_context_data(
            asistencias=sesion.asistencias.select_related("estudiante"),
            ausentes=Estudiante.objects.filter(activo=True).exclude(pk__in=presentes_ids),
            stats=estadisticas_sesion(sesion),
            **kwargs,
        )


@login_required
@require_POST
def sesion_cerrar(request, pk: int):
    sesion = get_object_or_404(SesionClase, pk=pk)
    cerrar_sesion(sesion)
    messages.success(request, "Sesión cerrada.")
    return redirect("asistencia:sesion_detalle", pk=pk)


def _csv_seguro(valor: str) -> str:
    """Evita inyección de fórmulas al abrir el CSV en Excel."""
    texto = str(valor)
    return f"'{texto}" if texto[:1] in ("=", "+", "-", "@") else texto


@login_required
def sesion_csv(request, pk: int):
    sesion = get_object_or_404(SesionClase, pk=pk)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="asistencia_sesion_{sesion.pk}.csv"'
    response.write("﻿")  # BOM para que Excel respete las tildes
    writer = csv.writer(response)
    writer.writerow(["Cédula", "Apellidos", "Nombres", "Estado", "Hora", "Similitud"])
    presentes = {a.estudiante_id: a for a in sesion.asistencias.all()}
    for estudiante in Estudiante.objects.filter(activo=True):
        asistencia = presentes.get(estudiante.pk)
        hora = timezone.localtime(asistencia.registrado).strftime("%H:%M:%S") if asistencia else ""
        writer.writerow(
            [
                _csv_seguro(estudiante.cedula),
                _csv_seguro(estudiante.apellidos),
                _csv_seguro(estudiante.nombres),
                "Presente" if asistencia else "Ausente",
                hora,
                f"{asistencia.similitud:.3f}" if asistencia else "",
            ]
        )
    return response


# ---------------------------------------------------------------------------
# Monitor en tiempo real
# ---------------------------------------------------------------------------


@login_required
def monitor(request):
    sesion = None
    raw = request.GET.get("sesion", "")
    if raw.isdigit():
        sesion = SesionClase.objects.filter(pk=int(raw)).first()
    if sesion is None:
        sesion = SesionClase.objects.filter(fin__isnull=True).first()
    contexto = {
        "sesion": sesion,
        "asistencias": sesion.asistencias.select_related("estudiante") if sesion else [],
        "stats": estadisticas_sesion(sesion) if sesion else None,
        "filtros": [(key, label) for key, (label, _) in VIEW_FILTERS.items()],
        "modelos_listos": _modelos_listos(),
    }
    return render(request, "asistencia/monitor.html", contexto)
