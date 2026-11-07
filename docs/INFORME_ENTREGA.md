# Informe de entrega — Práctica 3 (borrador para el PDF)

> Copie este contenido en la **plantilla oficial del aula virtual**, complete los datos y
> expórtelo a PDF. La guía pide un PDF con los enlaces del video y del repositorio.

**Universidad Estatal de Milagro — Facultad de Ciencias e Ingenierías**
**Carrera:** Software (presencial) · **Asignatura:** Construcción de Software
**Guía:** G003-S12 · **Práctica N.º 3** · **Docente:** _________ · **Docente de práctica:** _________
**Grupo:** ___ · **Fecha:** ___/___/2026

**Integrantes:**
1. _______________________
2. _______________________
3. _______________________
4. _______________________
5. _______________________

## 1. Objetivo

Diseñar y desarrollar un aplicativo web en Django que capture video en tiempo real, lo procese
con OpenCV, detecte y reconozca rostros, y muestre resultados útiles en una interfaz web
interactiva, aplicado al control de asistencia.

## 2. Temática seleccionada

Detección de rostros para control de asistencia.

## 3. Tecnologías

Python · Django · OpenCV (cv2: `FaceDetectorYN`, `FaceRecognizerSF`, CLAHE, Canny, Laplaciano) ·
PostgreSQL · HTML/CSS/JavaScript (`getUserMedia`) · Git/GitHub · Docker (opcional).

## 4. Desarrollo por sesiones

- **Sesión 1 — Configuración:** proyecto Django `config`, app `asistencia`, conexión a PostgreSQL,
  captura de la cámara en el navegador y transmisión de fotogramas al servidor.
- **Sesión 2 — Procesamiento y detección:** módulo `vision/` con detección YuNet, reconocimiento
  SFace, mejora CLAHE y anotación de resultados directamente sobre el video.
- **Sesión 3 — Interfaz y pruebas:** panel, monitor en vivo, gestión de estudiantes y sesiones,
  exportación CSV y 27 casos de prueba funcionales.

## 5. Capturas de pantalla

_(Insertar: login, panel, registro de rostro, monitor reconociendo, detalle de sesión.)_

## 6. Enlaces

| Entregable | Enlace |
|---|---|
| Video demostrativo (Google Drive, ≤ 3 min, permiso de visualización) | https://drive.google.com/________ |
| Repositorio GitHub (incluye README.md y requirements.txt, sin entorno virtual) | https://github.com/________/visionaula |

## 7. Conclusiones

1. _______________________
2. _______________________

## 8. Referencias

Pressman, R. S. (2005). *Ingeniería del software: un enfoque práctico*. México: McGraw-Hill.
OpenCV. (2024). *OpenCV Zoo: YuNet y SFace*. https://github.com/opencv/opencv_zoo
