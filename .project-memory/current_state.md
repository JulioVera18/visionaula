.Ñ.# Estado Actual del Proyecto — VisionAula

**Última actualización:** 2026-11-07  
**Rama activa:** `main`  
**Bóveda Obsidian:** `VisionAula Vault` (`C:\Users\Flavio\Documents\VisionAula Vault`)

---

## 📌 Resumen del Proyecto
Aplicativo web en Django para control de asistencia mediante reconocimiento facial en tiempo real (cámara web, OpenCV, YuNet, SFace, PostgreSQL/SQLite).

- **Stack:** Python 3.14 / Django 6.1, OpenCV (YuNet + SFace), SQLite/PostgreSQL, HTML/JS.
- **Entorno:** `venv/` configurado con dependencias base y dev (`pytest`, `pytest-django`, `pytest-cov`).

---

## 📋 Tareas

### Pendientes
- [ ] Ejecutar el servidor de desarrollo (`python manage.py runserver`).
- [ ] Probar el flujo de reconocimiento facial y login con el superusuario en `/admin/` o interfaz web.

### Completadas
- [x] Inicialización del repositorio y memoria del proyecto.
- [x] Despliegue de bóveda física independiente en Obsidian (`VisionAula Vault`).
- [x] Instalación de dependencias de desarrollo (`requirements-dev.txt`) y validación de 76 tests (`pytest`).
- [x] Configuración de credenciales de acceso de superusuario (`admin`).
