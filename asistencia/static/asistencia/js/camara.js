// Utilidades compartidas: acceso a la cámara, captura de fotogramas y envío al servidor.

const MAX_ANCHO = 1280; // HD 720p: buena nitidez sin saturar el servidor

export function csrfToken() {
  const input = document.querySelector("input[name=csrfmiddlewaretoken]");
  return input ? input.value : "";
}

export async function encenderCamara(video) {
  if (!navigator.mediaDevices?.getUserMedia) {
    throw new Error("Este navegador no permite acceder a la cámara (use Chrome/Edge/Firefox en localhost o HTTPS).");
  }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: "user" },
      audio: false,
    });
    video.srcObject = stream;
    await video.play();
    return stream;
  } catch (error) {
    if (error.name === "NotAllowedError") throw new Error("Permiso de cámara denegado. Habilítelo en el navegador.");
    if (error.name === "NotFoundError") throw new Error("No se encontró ninguna cámara conectada.");
    if (error.name === "NotReadableError") throw new Error("La cámara está siendo usada por otra aplicación.");
    throw new Error(`No se pudo iniciar la cámara: ${error.message}`);
  }
}

export function apagarCamara(stream) {
  stream?.getTracks().forEach((track) => track.stop());
}

// Copia el fotograma actual del <video> a un canvas y lo devuelve como JPEG.
export function capturarFotograma(video, canvas, calidad = 0.8) {
  const escala = Math.min(1, MAX_ANCHO / video.videoWidth);
  canvas.width = Math.round(video.videoWidth * escala);
  canvas.height = Math.round(video.videoHeight * escala);
  canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => (blob ? resolve(blob) : reject(new Error("No se pudo capturar el fotograma."))),
      "image/jpeg", calidad);
  });
}

// Envía la imagen como multipart/form-data y devuelve `data` del sobre JSON.
export async function enviarImagen(url, blob, extra = {}, signal) {
  const form = new FormData();
  form.append("frame", blob, "frame.jpg");
  Object.entries(extra).forEach(([clave, valor]) => form.append(clave, valor));
  const respuesta = await fetch(url, {
    method: "POST",
    body: form,
    headers: { "X-CSRFToken": csrfToken() },
    credentials: "same-origin",
    signal,
  });
  let cuerpo;
  try {
    cuerpo = await respuesta.json();
  } catch {
    throw new Error(`Respuesta inválida del servidor (HTTP ${respuesta.status}).`);
  }
  if (!cuerpo.ok) {
    const error = new Error(cuerpo.error || "Error desconocido.");
    error.status = respuesta.status;
    throw error;
  }
  return cuerpo.data;
}

export function mostrarEstado(elemento, texto, tipo = "") {
  elemento.textContent = texto;
  elemento.className = `status ${tipo}`.trim();
}
