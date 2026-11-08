# Casos de prueba — VisionAula

Pruebas funcionales que el equipo ejecuta con el sistema en funcionamiento (Sesión 3 de la guía).
Cada integrante puede ejecutarlos con la cámara de su computador.

**Entorno:** Windows 11, Python 3.x, PostgreSQL, Chrome, cámara integrada de laptop.
Marque el resultado obtenido en la última columna.

| ID | Funcionalidad | Pasos | Resultado esperado | Resultado |
|---|---|---|---|---|
| CP-01 | Inicio de sesión | Abrir `/`, ingresar usuario y contraseña válidos | Se muestra el Panel de control | ☐ OK ☐ Falla |
| CP-02 | Acceso protegido | Sin iniciar sesión, abrir `/monitor/` | Redirige a la página de login | ☐ OK ☐ Falla |
| CP-03 | Registrar estudiante | Estudiantes → Nuevo, llenar datos | Se guarda y abre la página *Registrar rostro* | ☐ OK ☐ Falla |
| CP-04 | Validación de cédula | Registrar con la cédula `0912345678` (dígito verificador incorrecto) | Error "La cédula no es válida: el dígito verificador no coincide." | ☐ OK ☐ Falla |
| CP-04b | Cédula duplicada | Registrar dos estudiantes con la misma cédula | Error "Ya existe un estudiante registrado con esta cédula." | ☐ OK ☐ Falla |
| CP-05 | Permiso de cámara denegado | Bloquear la cámara en el navegador y pulsar *Encender cámara* | Mensaje "Permiso de cámara denegado…" sin que la página falle | ☐ OK ☐ Falla |
| CP-06 | Enrolamiento automático | Encender cámara → *Captura automática (5)* | Se guardan 5 muestras con su puntaje de calidad | ☐ OK ☐ Falla |
| CP-07 | Enrolamiento sin rostro | Tapar la cámara y pulsar *Capturar foto* | "No se detectó ningún rostro." | ☐ OK ☐ Falla |
| CP-08 | Enrolamiento con 2 personas | Dos personas frente a la cámara → *Capturar foto* | "Hay más de un rostro…" | ☐ OK ☐ Falla |
| CP-09 | Enrolamiento borroso | Mover la cabeza rápido al capturar | "Imagen borrosa: mantén la cabeza quieta." | ☐ OK ☐ Falla |
| CP-10 | Subir foto | Elegir un archivo JPG con un rostro | La muestra aparece en la galería | ☐ OK ☐ Falla |
| CP-11 | Iniciar sesión de clase | Sesiones → asignatura → *Iniciar sesión* | Abre el monitor con la etiqueta EN CURSO | ☐ OK ☐ Falla |
| CP-12 | Una sola sesión activa | Intentar iniciar una segunda sesión | Mensaje de error; no se crea | ☐ OK ☐ Falla |
| CP-13 | Detección en tiempo real | Monitor → *Iniciar cámara* | Video con marco y 5 puntos faciales; contador de rostros y FPS | ☐ OK ☐ Falla |
| CP-14 | Reconocimiento | Estudiante registrado frente a la cámara | Marco verde con su nombre y similitud ≥ 0.40 | ☐ OK ☐ Falla |
| CP-15 | Registro de asistencia | Mantenerse frente a la cámara ~1 s | Barra de progreso llega al 100 %, marco azul `[OK]`, notificación y foto en "Registrados" | ☐ OK ☐ Falla |
| CP-16 | Sin duplicados | Seguir frente a la cámara | No se repite el registro | ☐ OK ☐ Falla |
| CP-17 | Persona no registrada | Persona sin enrolar frente a la cámara | Marco rojo "Desconocido"; no registra asistencia | ☐ OK ☐ Falla |
| CP-18 | Varios rostros | 2-3 estudiantes registrados a la vez | Todos reconocidos y registrados | ☐ OK ☐ Falla |
| CP-19 | Poca luz | Apagar la luz del aula / bajar el brillo | Aviso "Poca luz: mejora CLAHE aplicada" y el reconocimiento continúa | ☐ OK ☐ Falla |
| CP-20 | Filtros de procesamiento | Cambiar filtro a Grises, Bordes (Canny), Térmico, CLAHE | El video cambia en vivo y sigue mostrando detecciones | ☐ OK ☐ Falla |
| CP-21 | Privacidad automática | Poner frente a la cámara a una persona registrada y a otra no registrada | La no registrada aparece pixelada; la registrada se ve normal | ☐ OK ☐ Falla |
| CP-22 | Monitor sin sesión | Abrir el monitor sin sesión activa | Reconoce rostros pero no registra asistencia | ☐ OK ☐ Falla |
| CP-23 | Cerrar sesión de clase | Detalle → *Cerrar sesión* | Estado "Cerrada"; ya no registra asistencias | ☐ OK ☐ Falla |
| CP-24 | Estadísticas | Abrir el detalle de la sesión | Inscritos, presentes, ausentes y porcentaje correctos | ☐ OK ☐ Falla |
| CP-25 | Exportar CSV | *Exportar CSV* y abrir en Excel | Lista con Presente/Ausente, hora y similitud; tildes correctas | ☐ OK ☐ Falla |
| CP-26 | Servidor detenido | Detener `runserver` con el monitor abierto | Mensaje de error y el monitor se detiene tras varios intentos, sin bloquear la página | ☐ OK ☐ Falla |
| CP-27 | Modelos faltantes | Borrar `modelos/*.onnx` y abrir el monitor | Aviso "Faltan los modelos… descargar_modelos" | ☐ OK ☐ Falla |

## Resultados de la prueba con imágenes reales (verificación del pipeline)

Ejecutada con dos retratos de dominio público (NASA) a través de la API completa:

| Caso | Resultado |
|---|---|
| Enrolar foto válida | 201 Created, calidad 0.93 – 1.00 |
| Enrolar imagen sin rostro | 422 "No se detectó ningún rostro." |
| Enrolar imagen con dos rostros | 422 "Hay más de un rostro…" |
| Reconocer misma persona (imagen espejada y oscurecida al 45 %) | Reconocido, similitud 0.94, CLAHE activado automáticamente |
| Confirmación de asistencia | Registrada al 3er fotograma (progreso 0.33 → 0.67 → 1.0) |
| Dos personas en el mismo cuadro | Ambas reconocidas (0.95 y 0.92) y registradas |
| Persona no registrada | "Desconocido" con similitud 0.22, pixelada automáticamente |
| Tiempo de procesamiento por fotograma | ≈ 21 – 25 ms (sin contar el primer fotograma) |
