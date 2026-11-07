from django.contrib import admin

from .models import Asistencia, Estudiante, MuestraRostro, SesionClase


class MuestraInline(admin.TabularInline):
    model = MuestraRostro
    fields = ("imagen", "calidad", "creado")
    readonly_fields = ("imagen", "calidad", "creado")
    extra = 0


@admin.register(Estudiante)
class EstudianteAdmin(admin.ModelAdmin):
    list_display = ("codigo", "apellidos", "nombres", "curso", "activo")
    list_filter = ("activo", "curso")
    search_fields = ("codigo", "nombres", "apellidos")
    inlines = [MuestraInline]


@admin.register(SesionClase)
class SesionClaseAdmin(admin.ModelAdmin):
    list_display = ("asignatura", "tema", "docente", "inicio", "fin")
    list_filter = ("asignatura",)


@admin.register(Asistencia)
class AsistenciaAdmin(admin.ModelAdmin):
    list_display = ("estudiante", "sesion", "registrado", "similitud")
    list_filter = ("sesion",)
    search_fields = ("estudiante__nombres", "estudiante__apellidos", "estudiante__codigo")
