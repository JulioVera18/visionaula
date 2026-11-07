// Página de registro de rostro: captura manual, automática o subida de archivo.
import { apagarCamara, capturarFotograma, encenderCamara, enviarImagen, mostrarEstado } from "./camara.js";

const AUTO_TOTAL = 5;
const AUTO_PAUSA_MS = 900;

const esperar = (ms) => new Promise((r) => setTimeout(r, ms));

export function iniciarEnrolamiento({ url, maximo }) {
  const $ = (id) => document.getElementById(id);
  const video = $("video"), canvas = $("canvas"), estado = $("estado");
  const btnCamara = $("btn-camara"), btnCapturar = $("btn-capturar"), btnAuto = $("btn-auto");
  const galeria = $("galeria"), contador = $("contador"), archivo = $("archivo");
  let stream = null;
  let ocupado = false;

  function agregarMiniatura(data) {
    const figura = document.createElement("figure");
    const img = document.createElement("img");
    img.src = data.imagen;
    img.alt = "Nueva muestra";
    const pie = document.createElement("figcaption");
    pie.textContent = `Calidad ${data.calidad.toFixed(2)}`;
    figura.append(img, pie);
    galeria.prepend(figura);
    contador.textContent = data.total;
  }

  async function enviar(blob) {
    const data = await enviarImagen(url, blob);
    agregarMiniatura(data);
    return data;
  }

  async function capturarUna() {
    const blob = await capturarFotograma(video, canvas, 0.92);
    return enviar(blob);
  }

  function bloquear(valor) {
    ocupado = valor;
    btnCapturar.disabled = valor || !stream;
    btnAuto.disabled = valor || !stream;
  }

  btnCamara.addEventListener("click", async () => {
    if (stream) {
      apagarCamara(stream);
      stream = null;
      btnCamara.textContent = "Encender cámara";
      bloquear(false);
      return;
    }
    try {
      stream = await encenderCamara(video);
      btnCamara.textContent = "Apagar cámara";
      bloquear(false);
      mostrarEstado(estado, "Cámara lista. Mira al frente y captura.");
    } catch (error) {
      mostrarEstado(estado, error.message, "error");
    }
  });

  btnCapturar.addEventListener("click", async () => {
    if (ocupado) return;
    bloquear(true);
    try {
      const data = await capturarUna();
      mostrarEstado(estado, `Muestra guardada (${data.total}/${maximo}).`, "ok");
    } catch (error) {
      mostrarEstado(estado, error.message, "error");
    } finally {
      bloquear(false);
    }
  });

  btnAuto.addEventListener("click", async () => {
    if (ocupado) return;
    bloquear(true);
    let guardadas = 0, intentos = 0;
    while (guardadas < AUTO_TOTAL && intentos < AUTO_TOTAL * 4) {
      intentos += 1;
      try {
        const data = await capturarUna();
        guardadas += 1;
        mostrarEstado(estado, `Captura ${guardadas}/${AUTO_TOTAL}: gira levemente la cabeza…`, "ok");
        if (data.total >= maximo) break;
      } catch (error) {
        mostrarEstado(estado, `Reintentando: ${error.message}`, "error");
        if (error.status === 422 && /máximo/.test(error.message)) break;
      }
      await esperar(AUTO_PAUSA_MS);
    }
    mostrarEstado(estado, `Captura automática terminada: ${guardadas} muestras nuevas.`, guardadas ? "ok" : "error");
    bloquear(false);
  });

  archivo.addEventListener("change", async () => {
    const file = archivo.files[0];
    if (!file) return;
    try {
      const data = await enviar(file);
      mostrarEstado(estado, `Foto registrada (${data.total}/${maximo}).`, "ok");
    } catch (error) {
      mostrarEstado(estado, error.message, "error");
    } finally {
      archivo.value = "";
    }
  });

  window.addEventListener("pagehide", () => apagarCamara(stream));
}
