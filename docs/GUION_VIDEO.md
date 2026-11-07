# Guion del video demostrativo (máximo 3 minutos)

Requisitos de la guía: grabar **desde un computador** (no con celular), mostrar **todas** las
funcionalidades, durar **3 minutos como máximo**, subirlo a Google Drive y compartirlo con
permiso de visualización.

Herramientas sugeridas: OBS Studio o la Grabadora de pantalla de Windows (Win + Alt + R), con la cámara web encendida.

| Tiempo | Pantalla | Qué mostrar / decir |
|---|---|---|
| 0:00 – 0:15 | Panel | Presentación del equipo y del tema: "Control de asistencia con reconocimiento facial usando Django, OpenCV y PostgreSQL". |
| 0:15 – 0:35 | VS Code | Estructura del repositorio: módulo `vision/` (detección YuNet, reconocimiento SFace, procesamiento CLAHE) y app `asistencia/`. |
| 0:35 – 1:05 | Estudiantes | Crear un estudiante → *Captura automática (5)*. Mostrar el rechazo cuando no hay rostro o hay dos personas. |
| 1:05 – 1:15 | Sesiones | Iniciar la sesión de clase. |
| 1:15 – 2:00 | Monitor | Iniciar la cámara: detección con puntos faciales, reconocimiento por nombre, barra de confirmación, registro con notificación. Que entre una persona no registrada (marco rojo). Varias personas a la vez. |
| 2:00 – 2:25 | Monitor | Cambiar filtros (CLAHE, Canny, térmico), activar *Pixelar desconocidos* y bajar la luz para mostrar la corrección automática. |
| 2:25 – 2:45 | Detalle de sesión | Presentes con foto de evidencia, ausentes, porcentaje; cerrar la sesión y exportar CSV. |
| 2:45 – 3:00 | Terminal | `pytest`: 76 pruebas en verde. Cierre. |

Recordatorio: todos los integrantes deben participar (la guía exige presencia y participación para la calificación).
