from django.urls import path

from . import api, views

app_name = "asistencia"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("monitor/", views.monitor, name="monitor"),
    # Estudiantes
    path("estudiantes/", views.EstudianteListView.as_view(), name="estudiantes"),
    path("estudiantes/nuevo/", views.EstudianteCreateView.as_view(), name="estudiante_nuevo"),
    path("estudiantes/<int:pk>/editar/", views.EstudianteUpdateView.as_view(),
         name="estudiante_editar"),
    path("estudiantes/<int:pk>/eliminar/", views.estudiante_eliminar, name="estudiante_eliminar"),
    path("estudiantes/<int:pk>/rostro/", views.estudiante_enrolar, name="estudiante_enrolar"),
    path("muestras/<int:pk>/eliminar/", views.muestra_eliminar, name="muestra_eliminar"),
    # Sesiones
    path("sesiones/", views.sesiones, name="sesiones"),
    path("sesiones/<int:pk>/", views.SesionDetailView.as_view(), name="sesion_detalle"),
    path("sesiones/<int:pk>/cerrar/", views.sesion_cerrar, name="sesion_cerrar"),
    path("sesiones/<int:pk>/csv/", views.sesion_csv, name="sesion_csv"),
    # API JSON
    path("api/procesar/", api.procesar_frame, name="api_procesar"),
    path("api/estudiantes/<int:pk>/muestras/", api.registrar_muestra, name="api_muestra"),
]
