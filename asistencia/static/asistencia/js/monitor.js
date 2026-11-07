// Monitor en vivo: envía fotogramas al servidor (OpenCV) y muestra el video anotado.
import { apagarCamara, capturarFotograma, encenderCamara, enviarImagen, mostrarEstado } from "./camara.js";

const INTERVALO_MIN_MS = 80;      // tope ~12 FPS para no saturar el servidor
const ESPERA_ERROR_MS = 1500;     // pausa tras un error antes de reintentar
const MAX_ERRORES_SEGUIDOS = 5;

export function iniciarMonitor(config) {
  const $ = (id) => document.getElementById(id);
  const ui = {
    video: $("video"), salida: $("salida"), canvas: $("canvas"), placeholder: $("placeholder"),
    boton: $("btn-camara"), modo: $("modo"), privacidad: $("privacidad"), estado: $("estado"),
    rostros: $("m-rostros"), desc: $("m-desc"), ms: $("m-ms"), fps: $("m-fps"),
    enVivo: $("en-vivo"), registrados: $("registrados"), resumen: $("resumen"), barra: $("barra"),
    toast: $("toast"),
  };
  // `generacion` identifica cada arranque: un bucle viejo que despierta tras un
  // Detener/Iniciar rápido detecta que ya no es el vigente y termina.
  const estado = {
    stream: null, activo: false, errores: 0, presentes: config.presentes, abort: null, generacion: 0,
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
    const modo = config.sesion ? "Tomando asistencia…" : "Modo reconocimiento (sin registrar asistencia).";
    const resolucion = ui.video.dataset.resolucion ? ` Cámara: ${ui.video.dataset.resolucion}.` : "";
    mostrarEstado(ui.estado, modo + resolucion);
    bucle(estado.generacion);
  }

  function detener() {
    estado.activo = false;
    estado.generacion += 1;
    estado.abort?.abort();
    apagarCamara(estado.stream);
    estado.stream = null;
    ui.boton.textContent = "Iniciar cámara";
    ui.salida.hidden = true;
    ui.placeholder.hidden = false;
    mostrarEstado(ui.estado, "Cámara detenida.");
  }

  async function bucle(generacion) {
    const vigente = () => estado.activo && estado.generacion === generacion;
    let ultimo = performance.now();
    while (vigente()) {
      const inicio = performance.now();
      try {
        const data = await procesar();
        if (!vigente()) return;
        estado.errores = 0;
        pintar(data);
        const ahora = performance.now();
        ui.fps.textContent = (1000 / (ahora - ultimo)).toFixed(1);
        ultimo = ahora;
      } catch (error) {
        if (!vigente() || error.name === "AbortError") return;
        manejarError(error);
        await esperar(ESPERA_ERROR_MS);
      }
      await esperar(Math.max(0, INTERVALO_MIN_MS - (performance.now() - inicio)));
    }
  }

  async function procesar() {
    const blob = await capturarFotograma(ui.video, ui.canvas, 0.85);
    estado.abort = new AbortController();
    return enviarImagen(config.url, blob, {
      sesion: config.sesion,
      modo: ui.modo.value,
      privacidad: ui.privacidad.checked ? "1" : "0",
    }, estado.abort.signal);
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
    ui.salida.src = data.imagen;
    ui.salida.hidden = false;
    ui.rostros.textContent = data.total_rostros;
    ui.desc.textContent = data.desconocidos;
    ui.ms.textContent = `${Math.round(data.ms)} ms`;
    if (data.galeria_vacia) {
      mostrarEstado(ui.estado, "No hay rostros registrados: registre estudiantes para reconocerlos.", "error");
    } else if (data.poca_luz) {
      mostrarEstado(ui.estado, "Poca luz detectada: se aplica mejora de contraste (CLAHE).");
    }
    pintarDetectados(data.rostros);
    data.nuevas_asistencias.forEach(agregarAsistencia);
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
