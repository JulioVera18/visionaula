"""Módulo de visión por computadora de VisionAula.

Este paquete es independiente de Django: solo depende de OpenCV y NumPy,
por lo que puede reutilizarse en otros proyectos (scripts, APIs, etc.).

Etapas del pipeline:
    1. codec          -> decodificar / codificar imágenes JPEG.
    2. preprocessing  -> procesamiento de imagen (iluminación, calidad, filtros).
    3. detector       -> detección de rostros con la red YuNet (cv2.FaceDetectorYN).
    4. recognizer     -> reconocimiento facial con SFace (cv2.FaceRecognizerSF).
    5. annotator      -> dibujo de resultados sobre el video.
    6. pipeline       -> orquesta todas las etapas.
"""
