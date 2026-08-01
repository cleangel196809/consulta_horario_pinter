// Utilidades comunes para hablar con la API desde cualquier página.
const API_BASE = "/api";

function getToken() {
  return localStorage.getItem("ph_token");
}

function getRol() {
  return localStorage.getItem("ph_rol");
}

// Etiqueta legible para el badge de rol en la barra superior. Los roles
// "docente" y "consulta_estudiante" son de solo lectura, igual que
// "consulta", pero se muestran con su propia etiqueta para mayor claridad.
function etiquetaRol() {
  const r = getRol();
  if (r === "admin") return "Administrador";
  if (r === "coordinador") return "Coordinador";
  if (r === "docente") return "Docente";
  if (r === "consulta_estudiante") return "Consulta estudiante";
  return "Consulta";
}

function getNombreUsuario() {
  return localStorage.getItem("ph_nombre") || localStorage.getItem("ph_username") || "";
}

function cerrarSesion() {
  localStorage.removeItem("ph_token");
  localStorage.removeItem("ph_rol");
  localStorage.removeItem("ph_nombre");
  localStorage.removeItem("ph_username");
  window.location.href = "/index.html";
}

function exigirSesion() {
  if (!getToken()) {
    window.location.href = "/index.html";
  }
}

async function apiFetch(path, options = {}) {
  const headers = options.headers || {};
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const resp = await fetch(API_BASE + path, { ...options, headers });
  if (resp.status === 401) {
    cerrarSesion();
    throw new Error("Sesión expirada");
  }
  if (!resp.ok) {
    let detalle = "Ocurrió un error";
    try {
      const data = await resp.json();
      detalle = data.detail || detalle;
    } catch (e) {}
    throw new Error(detalle);
  }
  if (resp.status === 204) return null;
  return resp.json();
}

// ---------------------------------------------------------------------
// Grilla semanal de horario (usada en docentes.html y estudiantes.html).
// Ambas páginas consumen el mismo shape de datos (HorarioOut[]) y muestran
// el horario en formato de tabla semanal con franjas horarias fijas.
// ---------------------------------------------------------------------
const FRANJAS_HORARIO = [
  ["07:00", "08:30"],
  ["08:30", "10:00"],
  ["10:00", "11:30"],
  ["11:30", "13:00"],
  ["14:00", "15:30"],
  ["15:30", "17:00"],
  ["18:00", "19:30"],
  ["19:30", "21:00"],
];

function _normalizarHoraGrilla(h) {
  if (!h) return "";
  return h.length >= 5 ? h.slice(0, 5) : h;
}

function _franjaDeHorarioGrilla(horaInicio) {
  const hi = _normalizarHoraGrilla(horaInicio);
  for (const [inicio, fin] of FRANJAS_HORARIO) {
    if (hi === inicio) return `${inicio}-${fin}`;
  }
  return null;
}

function _ordenDiaGrilla(dia) {
  const m = /^(\d+)\./.exec(dia || "");
  return m ? parseInt(m[1], 10) : 99;
}

// Genera el HTML completo (thead + tbody) de la grilla semanal a partir de
// un arreglo de horarios (HorarioOut[]). `cedula` y `nombre` alimentan el
// encabezado; `totalSesiones`, si no se indica, se calcula como la
// cantidad de filas recibidas.
function construirGrillaHorarioHtml(cedula, nombre, horarios, totalSesiones) {
  horarios = horarios || [];
  const dias = [];
  horarios.forEach((h) => {
    const d = h.dia || "Sin día";
    if (!dias.includes(d)) dias.push(d);
  });
  dias.sort((a, b) => _ordenDiaGrilla(a) - _ordenDiaGrilla(b));

  const celdas = {};
  const otros = [];

  horarios.forEach((h) => {
    const franja = _franjaDeHorarioGrilla(h.hora_inicio);
    const dia = h.dia || "Sin día";
    if (!franja) {
      otros.push(h);
      return;
    }
    const key = `${franja}|${dia}`;
    if (!celdas[key]) celdas[key] = [];
    celdas[key].push(h);
  });

  const sesiones = typeof totalSesiones === "number" ? totalSesiones : horarios.length;
  const colspanDias = Math.max(dias.length, 1);

  const celdaHtml = (h) => `
    <div class="grilla-clase">
      <div class="grilla-asignatura">${h.asignatura || ""}</div>
      <div class="grilla-grupo">${h.grupo || ""}</div>
      <div class="grilla-sede">${[h.sede, h.nombre_salon].filter(Boolean).join(" - ")}</div>
    </div>`;

  let html = `<table class="grilla-horario">
    <thead>
      <tr>
        <th class="grilla-cabecera-izq">${cedula != null ? cedula : ""}</th>
        <th class="grilla-cabecera-nombre" colspan="${colspanDias}">${nombre || ""}</th>
        <th class="grilla-cabecera-der">Sesiones: ${sesiones}</th>
      </tr>
      <tr>
        <th class="grilla-esquina"></th>
        ${dias.map((d) => `<th class="grilla-dia">${d}</th>`).join("")}
        <th class="grilla-esquina"></th>
      </tr>
    </thead>
    <tbody>`;

  if (dias.length === 0) {
    html += `<tr><td colspan="3" style="text-align:center;color:#999;">Sin clases con horario asignado</td></tr>`;
  } else {
    FRANJAS_HORARIO.forEach(([inicio, fin]) => {
      const franja = `${inicio}-${fin}`;
      html += `<tr><td class="grilla-franja">${franja}</td>`;
      dias.forEach((d) => {
        const items = celdas[`${franja}|${d}`] || [];
        html += `<td class="grilla-celda">${items.map(celdaHtml).join("")}</td>`;
      });
      html += `<td class="grilla-esquina"></td></tr>`;
    });
  }

  if (otros.length) {
    html += `<tr><td class="grilla-franja">Otros horarios</td>`;
    html += `<td class="grilla-celda" colspan="${colspanDias}">`;
    html += otros
      .map((h) => {
        const hora =
          h.hora_inicio && h.hora_fin
            ? `${_normalizarHoraGrilla(h.hora_inicio)} - ${_normalizarHoraGrilla(h.hora_fin)}`
            : "";
        return `<div class="grilla-clase">
          <div class="grilla-asignatura">${h.asignatura || ""} (${h.dia || ""}${hora ? " " + hora : ""})</div>
          <div class="grilla-grupo">${h.grupo || ""}</div>
          <div class="grilla-sede">${[h.sede, h.nombre_salon].filter(Boolean).join(" - ")}</div>
        </div>`;
      })
      .join("");
    html += `</td><td class="grilla-esquina"></td></tr>`;
  }

  html += `</tbody></table>`;
  return html;
}

// Descarga un archivo protegido (PDF/ICS) inyectando el token de sesión,
// ya que un <a href> normal no puede enviar el header Authorization.
async function descargarArchivo(path, nombreArchivo) {
  const token = getToken();
  const resp = await fetch(API_BASE + path, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (resp.status === 401) {
    cerrarSesion();
    throw new Error("Sesión expirada");
  }
  if (!resp.ok) {
    let detalle = "No se pudo generar el archivo";
    try {
      const data = await resp.json();
      detalle = data.detail || detalle;
    } catch (e) {}
    throw new Error(detalle);
  }
  const blob = await resp.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = nombreArchivo;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}
