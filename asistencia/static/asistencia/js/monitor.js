// Monitor en vivo: el video se muestra directo de la cámara (fluido, resolución nativa)
// y en paralelo se envían copias reducidas al servidor para que OpenCV las analice.
// Los resultados se dibujan encima del video en cada cuadro (requestAnimationFrame).
// Con un filtro activo se muestra el fotograma procesado por OpenCV en el servidor.
import { apagarCamara, capturarFotograma, encenderCamara, enviarImagen, mostrarEstado } from "./camara.js";
import { dibujarOverlay, limpiarOverlay } from "./overlay.js";

const ENVIO = {
  normal: { ancho: 1280, calidad: 0.8 },  // solo análisis: buena precisión
  filtro: { ancho: 960, calidad: 0.7 },   // con imagen de vuelta: liviano para menos lag
};
const PETICIONES_EN_PARALELO = 2;  // mientras el servidor procesa una, se envía la siguiente
const INTERVALO_MIN_MS = 40;       // tope por trabajador
const ESPERA_ERROR_MS = 1500;      // pausa tras un error antes de reintentar
const MAX_ERRORES_SEGUIDOS = 5;

export function iniciarMonitor(config) {
  const $ = (id) => document.getElementById(id);
  const ui = {
    video: $("video"), salida: $("salida"), canvas: $("canvas"), placeholder: $("placeholder"),
    overlay: $("overlay"),
    boton: $("btn-camara"), modo: $("modo"), privacidad: $("privacidad"), estado: $("estado"),
    rostros: $("m-rostros"), desc: $("m-desc"), ms: $("m-ms"), fps: $("m-fps"),
    enVivo: $("en-vivo"), registrados: $("registrados"), resumen: $("resumen"), barra: $("barra"),
    toast: $("toast"),
  };
  // `generacion` identifica cada arranque: un bucle viejo que despierta tras un
  // Detener/Iniciar rápido detecta que ya no es el vigente y termina.
  // `secuencia` numera cada fotograma enviado; una respuesta más vieja que la ya
  // mostrada se descarta (con peticiones en paralelo pueden llegar desordenadas).
  const estado = {
    stream: null, activo: false, errores: 0, presentes: config.presentes, generacion: 0,
    peticiones: new Set(), secuencia: 0, ultimaMostrada: 0, ultimoInstante: 0,
    resultado: null,  // último análisis, redibujado en cada cuadro del video
  };

  ui.boton.addEventListener("click", () => (estado.activo ? detener() : iniciar()));
  window.addEventListener("pagehide", detener);

  async function iniciar() {
    ui.boton.disabled = true;  // evita dos arranques por doble clic
    try {
      estado.stream = await encenderCamara(ui.video);
    } catch (error) {
      mostrarEstado(ui.estado, error.message, "error");
      return;
    } finally {
      ui.boton.disabled = false;
    }
    estado.activo = true;
    estado.errores = 0;
    estado.generacion += 1;
    ui.boton.textContent = "Detener cámara";
    ui.placeholder.hidden = true;
    ui.video.hidden = false;
    const modo = config.sesion ? "Tomando asistencia…" : "Modo reconocimiento (sin registrar asistencia).";
    const resolucion = ui.video.dataset.resolucion ? ` Cámara: ${ui.video.dataset.resolucion}.` : "";
    mostrarEstado(ui.estado, modo + resolucion);
    estado.resultado = null;
    estado.ultimoInstante = performance.now();
    for (let i = 0; i < PETICIONES_EN_PARALELO; i++) bucle(estado.generacion);
    requestAnimationFrame(() => redibujar(estado.generacion));
  }

  function detener() {
    estado.activo = false;
    estado.generacion += 1;
    estado.peticiones.forEach((c) => c.abort());
    estado.peticiones.clear();
    estado.resultado = null;
    apagarCamara(estado.stream);
    estado.stream = null;
    ui.boton.textContent = "Iniciar cámara";
    ui.salida.hidden = true;
    ui.video.hidden = true;
    limpiarOverlay(ui.overlay);
    ui.placeholder.hidden = false;
    mostrarEstado(ui.estado, "Cámara detenida.");
  }

  // Cada trabajador captura, envía y espera su respuesta; varios en paralelo
  // aprovechan el tiempo de subida mientras el servidor procesa otro fotograma.
  async function bucle(generacion) {
    const vigente = () => estado.activo && estado.generacion === generacion;
    const lienzo = document.createElement("canvas");  // uno por trabajador
    while (vigente()) {
      const inicio = performance.now();
      try {
        const { data, secuencia } = await procesar(lienzo);
        if (!vigente()) return;
        estado.errores = 0;
        data.nuevas_asistencias.forEach(agregarAsistencia);  // nunca se descartan
        if (secuencia > estado.ultimaMostrada) {
          estado.ultimaMostrada = secuencia;
          pintar(data);
        }
      } catch (error) {
        if (!vigente() || error.name === "AbortError") return;
        manejarError(error);
        await esperar(ESPERA_ERROR_MS);
      }
      await esperar(Math.max(0, INTERVALO_MIN_MS - (performance.now() - inicio)));
    }
  }

  // Solo los filtros necesitan la imagen procesada por OpenCV; la privacidad se
  // aplica en el navegador sobre el video en vivo.
  const necesitaImagen = () => ui.modo.value !== "normal";

  async function procesar(lienzo) {
    const conImagen = necesitaImagen();
    const envio = conImagen ? ENVIO.filtro : ENVIO.normal;
    const secuencia = ++estado.secuencia;
    const blob = await capturarFotograma(ui.video, lienzo, envio.calidad, envio.ancho);
    const control = new AbortController();
    estado.peticiones.add(control);
    try {
      const data = await enviarImagen(config.url, blob, {
        sesion: config.sesion,
        modo: ui.modo.value,
        privacidad: ui.privacidad.checked ? "1" : "0",
        imagen: conImagen ? "1" : "0",
      }, control.signal);
      return { data, secuencia };
    } finally {
      estado.peticiones.delete(control);
    }
  }

  // Redibuja los últimos resultados en cada cuadro del video, así el pixelado
  // de privacidad sigue al video en tiempo real.
  function redibujar(generacion) {
    if (!estado.activo || estado.generacion !== generacion) return;
    const r = estado.resultado;
    if (r && !r.imagen) {
      dibujarOverlay(ui.overlay, ui.video, r.rostros, r.ancho, { privacidad: ui.privacidad.checked });
    }
    requestAnimationFrame(() => redibujar(generacion));
  }

  function manejarError(error) {
    estado.errores += 1;
    mostrarEstado(ui.estado, error.message, "error");
    if (error.status === 401 || error.status === 503 || estado.errores >= MAX_ERRORES_SEGUIDOS) {
      detener();
      mostrarEstado(ui.estado, `${error.message} (monitor detenido)`, "error");
    }
  }

  function pintar(data) {
    estado.resultado = data;
    if (data.imagen) {
      ui.salida.src = data.imagen;
      ui.salida.hidden = false;
      limpiarOverlay(ui.overlay);
    } else {
      ui.salida.hidden = true;
      // También se dibuja aquí por si el navegador pausa requestAnimationFrame.
      dibujarOverlay(ui.overlay, ui.video, data.rostros, data.ancho, { privacidad: ui.privacidad.checked });
    }
    const ahora = performance.now();
    ui.fps.textContent = (1000 / Math.max(ahora - estado.ultimoInstante, 1)).toFixed(1);
    estado.ultimoInstante = ahora;
    ui.rostros.textContent = data.total_rostros;
    ui.desc.textContent = data.desconocidos;
    ui.ms.textContent = `${Math.round(data.ms)} ms`;
    if (data.galeria_vacia) {
      mostrarEstado(ui.estado, "No hay rostros registrados: registre estudiantes para reconocerlos.", "error");
    } else if (data.poca_luz) {
      mostrarEstado(ui.estado, "Poca luz detectada: se aplica mejora de contraste (CLAHE).");
    }
    pintarDetectados(data.rostros);
  }

  function pintarDetectados(rostros) {
    ui.enVivo.replaceChildren();
    if (!rostros.length) {
      ui.enVivo.append(item("—", "", "muted"));
      return;
    }
    rostros.forEach((r) => {
      const conocido = r.estudiante_id !== null;
      const li = item(conocido ? r.nombre : "Desconocido", r.similitud.toFixed(2), conocido ? "" : "unknown");
      if (conocido) {
        const barra = document.createElement("div");
        barra.className = "bar";
        const relleno = document.createElement("span");
        relleno.style.width = `${Math.round(r.progreso * 100)}%`;
        barra.append(relleno);
        li.append(barra);
      }
      ui.enVivo.append(li);
    });
  }

  function agregarAsistencia(a) {
    if (!ui.registrados) return;
    ui.registrados.querySelector(".vacio")?.remove();
    const li = document.createElement("li");
    li.className = "nuevo";
    if (a.evidencia) {
      const img = document.createElement("img");
      img.className = "thumb";
      img.src = a.evidencia;
      img.alt = "";
      li.append(img);
    }
    const texto = document.createElement("div");
    const nombre = document.createElement("b");
    nombre.textContent = a.estudiante;
    const hora = document.createElement("span");
    hora.className = "muted";
    hora.textContent = new Date(a.hora).toLocaleTimeString();
    texto.append(nombre, hora);
    li.append(texto);
    ui.registrados.prepend(li);
    estado.presentes += 1;
    actualizarResumen();
    notificar(`✓ Asistencia registrada: ${a.estudiante}`);
  }

  function actualizarResumen() {
    if (!ui.resumen) return;
    ui.resumen.textContent = `${estado.presentes}/${config.inscritos}`;
    const porcentaje = config.inscritos ? (estado.presentes * 100) / config.inscritos : 0;
    ui.barra.style.width = `${Math.min(100, porcentaje)}%`;
  }

  let temporizadorToast;
  function notificar(texto) {
    ui.toast.textContent = texto;
    ui.toast.hidden = false;
    clearTimeout(temporizadorToast);
    temporizadorToast = setTimeout(() => (ui.toast.hidden = true), 3000);
  }
}

function item(texto, valor, clase) {
  const li = document.createElement("li");
  const nombre = document.createElement("span");
  nombre.textContent = texto;
  if (clase) nombre.className = clase;
  const dato = document.createElement("span");
  dato.className = "mono muted";
  dato.textContent = valor;
  li.append(nombre, dato);
  return li;
}

const esperar = (ms) => new Promise((r) => setTimeout(r, ms));
