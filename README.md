# VisionAula: Control de asistencia con reconocimiento facial

## Integrantes

1. Flavio Josueph Morales Pluas
2. Fernando Alexander Pazmiño Soto
3. Grace Valeria Roa Cornejo
4. Julio Andrés Vera Garcias
5. Mauro Marcelo López León

## Descripción

VisionAula es un aplicativo web desarrollado en Django que permite registrar la asistencia
de los estudiantes mediante reconocimiento facial. El sistema captura video en tiempo real
desde la cámara del computador, procesa cada imagen con OpenCV, detecta y reconoce los
rostros, y guarda la asistencia en una base de datos PostgreSQL.

**Temática elegida:** Detección de rostros para control de asistencia.

## Objetivo

Diseñar y desarrollar un aplicativo web en Django que capture video en tiempo real, lo
procese con OpenCV, detecte y reconozca rostros, y muestre los resultados al usuario en
una interfaz web interactiva.

## Tecnologías utilizadas

- Python 3.10 o superior
- Django
- OpenCV
- PostgreSQL
- HTML, CSS y JavaScript

## Funcionalidades

- **Detección de rostros:** se usa el modelo YuNet de OpenCV para encontrar los rostros en el video.
- **Reconocimiento facial:** se usa el modelo SFace de OpenCV para identificar a cada estudiante registrado.
- **Procesamiento de imagen:** mejora automática cuando hay poca luz y filtros de visualización (escala de grises, bordes y mapa térmico).
- **Registro de estudiantes:** se toman entre 3 y 5 fotos del rostro de cada estudiante.
- **Sesiones de clase:** el docente abre una sesión y el sistema registra la asistencia automáticamente.
- **Reportes:** lista de presentes y ausentes, porcentaje de asistencia y exportación a CSV.
- **Modo privacidad:** pixela los rostros de personas no registradas o todos los rostros.

## Estructura del proyecto

```
visionaula/
├── config/          Configuración del proyecto Django
├── asistencia/      Aplicación principal (modelos, vistas, plantillas)
├── vision/          Módulo de procesamiento con OpenCV
├── templates/       Plantillas generales (base y login)
├── modelos/         Modelos de OpenCV (se descargan con un comando)
├── docs/            Casos de prueba y capturas
├── manage.py
└── requirements.txt
```

## Instalación

1. Clonar el repositorio:

   ```bash
   git clone https://github.com/JulioVera18/visionaula.git
   cd visionaula
   ```

2. Crear y activar el entorno virtual:

   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

3. Instalar las dependencias:

   ```bash
   pip install -r requirements.txt
   ```

4. Crear la base de datos en PostgreSQL:

   ```sql
   CREATE DATABASE visionaula;
   ```

5. Copiar el archivo `.env.example` con el nombre `.env` y colocar los datos de conexión a PostgreSQL.

6. Aplicar las migraciones, descargar los modelos y crear un usuario:

   ```bash
   python manage.py migrate
   python manage.py descargar_modelos
   python manage.py createsuperuser
   ```

7. Ejecutar el servidor:

   ```bash
   python manage.py runserver
   ```

8. Abrir en el navegador: <http://localhost:8000>

## Uso

1. Iniciar sesión con el usuario creado.
2. Ir a **Estudiantes**, registrar un estudiante y capturar fotos de su rostro.
3. Ir a **Sesiones** e iniciar una sesión de clase.
4. Abrir el **Monitor en vivo** y encender la cámara.
5. Cuando el sistema reconoce a un estudiante, registra su asistencia automáticamente.
6. Al terminar, cerrar la sesión y descargar el reporte en CSV.

## Capturas

**Reconocimiento facial**

![Reconocimiento facial](docs/img/05-reconocimiento.jpg)

**Panel de control**

![Panel de control](docs/img/02-panel.jpg)

**Detalle de una sesión**

![Detalle de sesión](docs/img/06-detalle-sesion.jpg)

## Pruebas

Los casos de prueba realizados se encuentran en el archivo
[docs/CASOS_DE_PRUEBA.md](docs/CASOS_DE_PRUEBA.md).
