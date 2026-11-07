# Modelos ONNX

Esta carpeta guarda los modelos oficiales de [OpenCV Zoo](https://github.com/opencv/opencv_zoo).
No se suben al repositorio por su tamaño. Descárguelos con:

```bash
python manage.py descargar_modelos
```

| Archivo | Uso | Tamaño |
|---|---|---|
| `face_detection_yunet_2023mar.onnx` | Detección de rostros (`cv2.FaceDetectorYN`) | ~230 KB |
| `face_recognition_sface_2021dec.onnx` | Reconocimiento facial (`cv2.FaceRecognizerSF`) | ~37 MB |

El comando verifica la integridad de cada archivo con SHA-256.
