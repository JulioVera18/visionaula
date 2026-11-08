// Dibuja sobre el video en vivo los resultados que devuelve OpenCV (recuadros,
// puntos faciales y nombres). Así el video se ve fluido en su resolución nativa
// y al servidor solo viaja la información de los rostros.

const COLORES = {
  conocido: "rgb(60, 200, 80)",
  confirmado: "rgb(30, 170, 255)",
  desconocido: "rgb(230, 60, 40)",
  punto: "rgb(255, 220, 0)",
};

export function limpiarOverlay(canvas) {
  canvas.getContext("2d").clearRect(0, 0, canvas.width, canvas.height);
}

const BLOQUES_PIXELADO = 10;

/**
 * @param {HTMLCanvasElement} canvas  lienzo superpuesto al video
 * @param {HTMLVideoElement} video
 * @param {Array} rostros  rostros devueltos por /api/procesar/
 * @param {number} ancho  ancho de la imagen que analizó el servidor
 */
export function dibujarOverlay(canvas, video, rostros, ancho) {
  const ctx = prepararLienzo(canvas);
  if (!video.videoWidth || !ancho) return;
  const area = areaVisible(canvas, video);
  const k = area.ancho / ancho;
  const punto = (x, y) => [area.x + x * k, area.y + y * k];
  // Privacidad: quien no está registrado se pixela automáticamente.
  const escalaVideo = video.videoWidth / ancho;
  rostros.filter((r) => r.estudiante_id === null)
    .forEach((r) => pixelar(ctx, video, r.box, escalaVideo, punto, k));
  rostros.forEach((rostro) => dibujarRostro(ctx, rostro, punto, k));
}

// Copia la región del rostro desde el video en muy baja resolución y la amplía
// sin suavizado: el resultado es un pixelado que sigue al video en tiempo real.
function pixelar(ctx, video, box, escalaVideo, punto, k) {
  const [bx, by, bw, bh] = box;
  const [x, y] = punto(bx, by);
  ctx.save();
  ctx.imageSmoothingEnabled = false;
  const tmp = pixelar.lienzo || (pixelar.lienzo = document.createElement("canvas"));
  tmp.width = BLOQUES_PIXELADO;
  tmp.height = BLOQUES_PIXELADO;
  tmp.getContext("2d").drawImage(video, bx * escalaVideo, by * escalaVideo, bw * escalaVideo,
    bh * escalaVideo, 0, 0, BLOQUES_PIXELADO, BLOQUES_PIXELADO);
  ctx.drawImage(tmp, x, y, bw * k, bh * k);
  ctx.restore();
}

function prepararLienzo(canvas) {
  const dpr = window.devicePixelRatio || 1;
  const w = canvas.clientWidth, h = canvas.clientHeight;
  if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) {
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
  }
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, h);
  return ctx;
}

// Rectángulo que ocupa el video dentro del recuadro (object-fit: contain).
function areaVisible(canvas, video) {
  const w = canvas.clientWidth, h = canvas.clientHeight;
  const escala = Math.min(w / video.videoWidth, h / video.videoHeight);
  const ancho = video.videoWidth * escala, alto = video.videoHeight * escala;
  return { x: (w - ancho) / 2, y: (h - alto) / 2, ancho, alto };
}

function dibujarRostro(ctx, rostro, punto, k) {
  const conocido = rostro.estudiante_id !== null;
  const color = !conocido ? COLORES.desconocido : rostro.confirmado ? COLORES.confirmado : COLORES.conocido;
  const [bx, by, bw, bh] = rostro.box;
  const [x, y] = punto(bx, by);
  const w = bw * k, h = bh * k;

  ctx.strokeStyle = color;
  ctx.lineWidth = 1.5;
  ctx.strokeRect(x, y, w, h);
  dibujarEsquinas(ctx, x, y, w, h);

  ctx.fillStyle = COLORES.punto;
  rostro.puntos.forEach(([px, py]) => {
    const [cx, cy] = punto(px, py);
    ctx.beginPath();
    ctx.arc(cx, cy, 2.5, 0, Math.PI * 2);
    ctx.fill();
  });

  const nombre = conocido ? rostro.nombre : "Desconocido";
  const texto = `${nombre} ${rostro.similitud.toFixed(2)}${rostro.confirmado ? " ✓" : ""}`;
  dibujarEtiqueta(ctx, texto, x, y, color);
  if (conocido && !rostro.confirmado && rostro.progreso > 0) {
    dibujarProgreso(ctx, x, y + h + 4, w, rostro.progreso, color);
  }
}

function dibujarEsquinas(ctx, x, y, w, h) {
  const largo = Math.max(Math.min(w, h) * 0.22, 8);
  ctx.lineWidth = 4;
  ctx.beginPath();
  [[x, y, 1, 1], [x + w, y, -1, 1], [x, y + h, 1, -1], [x + w, y + h, -1, -1]].forEach(([cx, cy, dx, dy]) => {
    ctx.moveTo(cx + dx * largo, cy);
    ctx.lineTo(cx, cy);
    ctx.lineTo(cx, cy + dy * largo);
  });
  ctx.stroke();
}

function dibujarEtiqueta(ctx, texto, x, y, color) {
  ctx.font = "600 15px 'Segoe UI', system-ui, sans-serif";
  const ancho = ctx.measureText(texto).width + 12;
  const alto = 24;
  const top = Math.max(y - alto - 4, 0);
  ctx.fillStyle = color;
  ctx.fillRect(x, top, ancho, alto);
  ctx.fillStyle = "#fff";
  ctx.textBaseline = "middle";
  ctx.fillText(texto, x + 6, top + alto / 2);
}

function dibujarProgreso(ctx, x, y, w, progreso, color) {
  ctx.fillStyle = "rgba(0, 0, 0, 0.55)";
  ctx.fillRect(x, y, w, 5);
  ctx.fillStyle = color;
  ctx.fillRect(x, y, w * progreso, 5);
}
