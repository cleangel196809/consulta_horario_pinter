exigirSesion();
document.getElementById("nombreUsuario").textContent = getNombreUsuario();
document.getElementById("badgeRol").textContent = etiquetaRol();
if (esAdministrador()) document.getElementById("tabAdmin").classList.remove("oculto");

const rol = getRol();
const rolesConsulta = ["admin", "administrador", "bienestar_universitario", "decano", "coordinador"];
const puedeEventos = ["admin", "administrador", "bienestar_universitario"].includes(rol);
const puedeAsistencia = ["admin", "administrador", "bienestar_universitario", "coordinador"].includes(rol);
const puedeValidar = ["admin", "administrador", "decano"].includes(rol);
let ceremoniaActual = null;

if (!rolesConsulta.includes(rol)) {
  document.getElementById("contenido").innerHTML = '<div class="card"><h2>Acceso restringido</h2><p>Tu rol no tiene permisos para consultar asistencia a grados.</p></div>';
} else {
  document.getElementById("crearCeremonia").classList.toggle("oculto", !puedeEventos);
  document.getElementById("agregarGraduando").classList.toggle("oculto", !puedeAsistencia);
  cargarCeremonias();
}

function celda(texto) {
  const td = document.createElement("td");
  td.textContent = texto == null ? "" : String(texto);
  return td;
}

async function cargarCeremonias() {
  const items = await apiFetch("/grados/ceremonias");
  const tbody = document.getElementById("ceremonias");
  tbody.replaceChildren();
  items.forEach((item) => {
    const tr = document.createElement("tr");
    [item.fecha, item.nombre, item.lugar, [item.facultad, item.programa].filter(Boolean).join(" · ")].forEach((v) => tr.appendChild(celda(v)));
    const accion = celda("");
    const boton = document.createElement("button");
    boton.className = "secundario";
    boton.textContent = "Abrir";
    boton.onclick = () => abrirCeremonia(item);
    accion.appendChild(boton);
    tr.appendChild(accion);
    tbody.appendChild(tr);
  });
}

async function abrirCeremonia(item) {
  ceremoniaActual = item;
  document.getElementById("detalle").classList.remove("oculto");
  document.getElementById("tituloCeremonia").textContent = item.nombre;
  document.getElementById("graduandoFacultad").value = item.facultad || "";
  document.getElementById("graduandoPrograma").value = item.programa || "";
  const [graduandos, reporte] = await Promise.all([
    apiFetch(`/grados/ceremonias/${item.id}/graduandos`),
    apiFetch(`/grados/ceremonias/${item.id}/reporte`),
  ]);
  document.getElementById("total").textContent = reporte.total_graduandos;
  document.getElementById("presentes").textContent = reporte.presentes;
  document.getElementById("ausentes").textContent = reporte.ausentes;
  document.getElementById("pendientes").textContent = reporte.pendientes;
  const tbody = document.getElementById("graduandos");
  tbody.replaceChildren();
  graduandos.forEach((g) => {
    const tr = document.createElement("tr");
    [g.estudiante_cedula, g.facultad, g.programa, g.validado ? "Sí" : "No"].forEach((v) => tr.appendChild(celda(v)));
    const accion = celda("");
    if (puedeAsistencia) {
      const boton = document.createElement("button");
      boton.className = "secundario";
      boton.textContent = "Registrar presente";
      boton.onclick = async () => {
        await apiFetch("/grados/asistencias", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({graduando_id: g.id, presente: true})});
        await abrirCeremonia(ceremoniaActual);
      };
      accion.appendChild(boton);
    }
    if (puedeValidar && !g.validado) {
      const validar = document.createElement("button");
      validar.className = "secundario";
      validar.textContent = "Validar";
      validar.onclick = async () => {
        await apiFetch(`/grados/graduandos/${g.id}/validar`, {method: "PATCH"});
        await abrirCeremonia(ceremoniaActual);
      };
      accion.appendChild(validar);
    }
    if (!puedeAsistencia && (!puedeValidar || g.validado)) accion.textContent = "Solo consulta";
    tr.appendChild(accion);
    tbody.appendChild(tr);
  });
}

if (puedeEventos) document.getElementById("formCeremonia").addEventListener("submit", async (event) => {
  event.preventDefault();
  await apiFetch("/grados/ceremonias", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({
    nombre: document.getElementById("ceremoniaNombre").value,
    fecha: document.getElementById("ceremoniaFecha").value,
    lugar: document.getElementById("ceremoniaLugar").value,
    facultad: document.getElementById("ceremoniaFacultad").value || null,
    programa: document.getElementById("ceremoniaPrograma").value || null,
  })});
  event.target.reset();
  await cargarCeremonias();
});

if (puedeAsistencia) document.getElementById("formGraduando").addEventListener("submit", async (event) => {
  event.preventDefault();
  await apiFetch(`/grados/ceremonias/${ceremoniaActual.id}/graduandos`, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({
    estudiante_cedula: document.getElementById("graduandoCedula").value,
    facultad: document.getElementById("graduandoFacultad").value,
    programa: document.getElementById("graduandoPrograma").value,
  })});
  document.getElementById("graduandoCedula").value = "";
  await abrirCeremonia(ceremoniaActual);
});
