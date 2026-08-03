exigirSesion();
document.getElementById("nombreUsuario").textContent = getNombreUsuario();
document.getElementById("badgeRol").textContent = etiquetaRol();

if (getRol() !== "admin") {
  document.getElementById("contenidoAdmin").innerHTML =
    '<div class="card"><h2>Acceso restringido</h2><p>Esta sección solo está disponible para usuarios con rol de administrador.</p></div>';
} else {
  inicializarAdmin();
}

function inicializarAdmin() {
  document.getElementById("formPlaneacion").addEventListener("submit", async (e) => {
    e.preventDefault();
    await manejarEnvioPlaneacion();
  });

  document.getElementById("formInscritos").addEventListener("submit", async (e) => {
    e.preventDefault();
    await subirArchivo("inscritos", "periodoInscritos", "archivoInscritos", "msgInscritos", "/admin/cargar-inscritos");
  });

  cargarHistorial();
  cargarUsuarios();
}

function iniciarNuevoCiclo() {
  const periodo = document.getElementById("periodoNuevoCiclo").value.trim();
  if (!periodo) {
    alert("Escribe el período del nuevo ciclo (ej. 2026-3T)");
    return;
  }
  document.getElementById("periodoPlaneacion").value = periodo;
  document.getElementById("periodoInscritos").value = periodo;
  document.getElementById("formPlaneacion").scrollIntoView({ behavior: "smooth", block: "center" });
}

function toggleCamposCoordinador() {
  const esCoordinador = document.getElementById("nuevoRol").value === "coordinador";
  document.getElementById("campoFacultadAlcance").classList.toggle("oculto", !esCoordinador);
  document.getElementById("campoSedeAlcance").classList.toggle("oculto", !esCoordinador);
}

async function subirArchivo(tipo, idPeriodo, idArchivo, idMsg, endpoint) {
  const periodo = document.getElementById(idPeriodo).value.trim();
  const archivoInput = document.getElementById(idArchivo);
  const msg = document.getElementById(idMsg);
  msg.style.display = "none";

  if (!archivoInput.files.length) {
    alert("Selecciona un archivo Excel");
    return;
  }

  const formData = new FormData();
  formData.append("periodo", periodo);
  formData.append("archivo", archivoInput.files[0]);

  try {
    const resp = await fetch(API_BASE + endpoint, {
      method: "POST",
      headers: { Authorization: `Bearer ${getToken()}` },
      body: formData,
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || "Error al cargar el archivo");

    msg.textContent = `Carga completada: ${data.filas_procesadas} fila(s) procesadas, ${data.filas_error} con error.`;
    msg.style.display = "block";
    cargarHistorial();
  } catch (err) {
    alert("Error: " + err.message);
  }
}

// ---------------------------------------------------------------------
// Carga de PLANEACIÓN con previsualización de duplicados: antes de
// insertar nada, se llama a /admin/cargar-planeacion/previsualizar; si
// encuentra duplicados se le pregunta al admin qué hacer y solo después
// se llama al endpoint real /admin/cargar-planeacion con
// eliminar_duplicados=true/false.
// ---------------------------------------------------------------------
let pendienteCargaPlaneacion = null; // { periodo, archivo }

async function manejarEnvioPlaneacion() {
  const periodo = document.getElementById("periodoPlaneacion").value.trim();
  const archivoInput = document.getElementById("archivoPlaneacion");
  const msg = document.getElementById("msgPlaneacion");
  msg.style.display = "none";
  document.getElementById("cardDuplicadosPlaneacion").classList.add("oculto");

  if (!archivoInput.files.length) {
    alert("Selecciona un archivo Excel");
    return;
  }

  const archivo = archivoInput.files[0];
  pendienteCargaPlaneacion = { periodo, archivo };

  try {
    const formData = new FormData();
    formData.append("periodo", periodo);
    formData.append("archivo", archivo);
    const resp = await fetch(API_BASE + "/admin/cargar-planeacion/previsualizar", {
      method: "POST",
      headers: { Authorization: `Bearer ${getToken()}` },
      body: formData,
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || "Error al previsualizar el archivo");

    if (data.duplicados_encontrados > 0) {
      mostrarDuplicadosPlaneacion(data);
    } else {
      await ejecutarCargaPlaneacion(false);
    }
  } catch (err) {
    alert("Error: " + err.message);
  }
}

function mostrarDuplicadosPlaneacion(data) {
  const card = document.getElementById("cardDuplicadosPlaneacion");
  document.getElementById("mensajeDuplicadosPlaneacion").textContent =
    `Se encontraron ${data.duplicados_encontrados} grupo(s) de clases duplicadas en el período ${data.periodo}. ¿Deseas eliminarlas antes de cargar?`;

  const tbody = document.getElementById("tbodyDuplicadosPlaneacion");
  tbody.innerHTML = "";
  (data.grupos_duplicados || []).forEach((g) => {
    const tr = document.createElement("tr");
    const hora = g.hora_inicio && g.hora_fin ? `${g.hora_inicio} - ${g.hora_fin}` : "";
    tr.innerHTML = `<td>${g.nombre_docente || g.docente_cedula || ""}</td><td>${g.dia || ""}</td><td>${hora}</td><td>${g.nombre_salon || ""}</td><td>${g.grupo || ""}</td><td>${g.asignatura || ""}</td><td>${g.veces_repetido || ""}</td>`;
    tbody.appendChild(tr);
  });

  card.classList.remove("oculto");
  card.scrollIntoView({ behavior: "smooth", block: "center" });
}

async function confirmarCargaPlaneacion(eliminarDuplicados) {
  document.getElementById("cardDuplicadosPlaneacion").classList.add("oculto");
  await ejecutarCargaPlaneacion(eliminarDuplicados);
}

function cancelarCargaPlaneacion() {
  document.getElementById("cardDuplicadosPlaneacion").classList.add("oculto");
  pendienteCargaPlaneacion = null;
}

async function ejecutarCargaPlaneacion(eliminarDuplicados) {
  if (!pendienteCargaPlaneacion) return;
  const { periodo, archivo } = pendienteCargaPlaneacion;
  const msg = document.getElementById("msgPlaneacion");

  const formData = new FormData();
  formData.append("periodo", periodo);
  formData.append("archivo", archivo);
  formData.append("eliminar_duplicados", eliminarDuplicados ? "true" : "false");

  try {
    const resp = await fetch(API_BASE + "/admin/cargar-planeacion", {
      method: "POST",
      headers: { Authorization: `Bearer ${getToken()}` },
      body: formData,
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || "Error al cargar el archivo");

    msg.textContent = `Carga completada: ${data.filas_procesadas} fila(s) procesadas, ${data.filas_error} con error.`;
    msg.style.display = "block";
    cargarHistorial();
  } catch (err) {
    alert("Error: " + err.message);
  } finally {
    pendienteCargaPlaneacion = null;
  }
}

const nombresDeCargas = {}; // cargaId -> nombre_archivo, usado por eliminarCarga() para el mensaje de confirmación

async function cargarHistorial() {
  try {
    const data = await apiFetch("/admin/cargas");
    const tbody = document.getElementById("tbodyHistorial");
    tbody.innerHTML = "";
    data.forEach((c) => {
      nombresDeCargas[c.id] = c.nombre_archivo || "";
      const tr = document.createElement("tr");
      const fecha = c.creado_en ? new Date(c.creado_en).toLocaleString() : "";
      tr.innerHTML = `<td>${fecha}</td><td>${c.tipo}</td><td>${c.nombre_archivo || ""}</td><td>${c.periodo || ""}</td><td>${c.filas_procesadas}</td><td>${c.duplicados_omitidos || 0}</td><td>${c.filas_error}</td><td>${c.estado}</td>
        <td><button class="secundario" onclick="notificarCarga(${c.id})">Notificar</button></td>
        <td><button class="secundario" style="color:#b3261e;border-color:#b3261e;" onclick="eliminarCarga(${c.id})">Eliminar</button></td>`;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error(err);
  }
}

async function eliminarCarga(cargaId) {
  const nombreArchivo = nombresDeCargas[cargaId] || `carga #${cargaId}`;
  if (
    !confirm(
      `¿Seguro que deseas eliminar el archivo "${nombreArchivo}" y TODOS los horarios/inscripciones que cargó?\n\n` +
        "Esta acción no se puede deshacer. Úsala cuando el Excel tenía errores y vas a volver a subir una versión corregida."
    )
  )
    return;
  try {
    const data = await apiFetch(`/admin/cargas/${cargaId}`, { method: "DELETE" });
    alert(`Carga eliminada. Filas eliminadas: ${data.filas_eliminadas}.`);
    cargarHistorial();
  } catch (err) {
    alert("Error: " + err.message);
  }
}

async function notificarCarga(cargaId) {
  try {
    const data = await apiFetch(`/admin/cargas/${cargaId}/notificar`, { method: "POST" });
    if (!data.habilitado) {
      alert(data.mensaje);
    } else {
      alert(`Correos enviados: ${data.enviados}. Fallidos: ${data.fallidos}.`);
    }
  } catch (err) {
    alert("Error: " + err.message);
  }
}

async function cargarUsuarios() {
  try {
    const data = await apiFetch("/usuarios");
    const tbody = document.getElementById("tbodyUsuarios");
    tbody.innerHTML = "";
    data.forEach((u) => {
      const alcance = [u.facultad_alcance, u.sede_alcance].filter(Boolean).join(" / ") || "—";
      const tr = document.createElement("tr");
      tr.innerHTML = `<td>${u.username}</td><td>${u.nombre_completo || ""}</td><td>${u.rol}</td><td>${alcance}</td><td>${u.activo ? "Sí" : "No"}</td>
        <td><button class="secundario" onclick="cambiarEstadoUsuario(${u.id}, ${!u.activo})">${u.activo ? "Desactivar" : "Activar"}</button></td>`;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error(err);
  }
}

async function crearUsuario() {
  const username = document.getElementById("nuevoUsername").value.trim();
  const password = document.getElementById("nuevoPassword").value;
  const nombre_completo = document.getElementById("nuevoNombre").value.trim();
  const rol = document.getElementById("nuevoRol").value;
  const facultad_alcance = document.getElementById("nuevaFacultadAlcance").value.trim();
  const sede_alcance = document.getElementById("nuevaSedeAlcance").value.trim();

  if (!username || !password) {
    alert("Usuario y contraseña son obligatorios");
    return;
  }
  if (rol === "coordinador" && !facultad_alcance && !sede_alcance) {
    alert("Un coordinador necesita al menos una facultad o sede de alcance");
    return;
  }

  try {
    await apiFetch("/usuarios", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password, nombre_completo, rol, facultad_alcance, sede_alcance }),
    });
    document.getElementById("nuevoUsername").value = "";
    document.getElementById("nuevoPassword").value = "";
    document.getElementById("nuevoNombre").value = "";
    document.getElementById("nuevaFacultadAlcance").value = "";
    document.getElementById("nuevaSedeAlcance").value = "";
    cargarUsuarios();
  } catch (err) {
    alert("Error: " + err.message);
  }
}

async function cambiarEstadoUsuario(id, nuevoEstado) {
  try {
    await apiFetch(`/usuarios/${id}/estado?activo=${nuevoEstado}`, { method: "PATCH" });
    cargarUsuarios();
  } catch (err) {
    alert("Error: " + err.message);
  }
}

// ---------------------------------------------------------------------
// Mantenimiento de base de datos: CRUD de horarios e inscripciones.
// Se guarda el último resultado de búsqueda en un cache en memoria para
// poder recuperar el objeto completo al pulsar "Editar" (evita tener que
// volver a pedirlo al backend y evita inyectar JSON crudo en atributos
// onclick, que se rompería con nombres que traigan comillas).
// ---------------------------------------------------------------------
let horariosCacheAdmin = [];
let idHorarioEnEdicion = null;

async function buscarHorariosAdmin() {
  const params = new URLSearchParams();
  const periodo = document.getElementById("bhPeriodo").value.trim();
  const dia = document.getElementById("bhDia").value.trim();
  const docenteCedula = document.getElementById("bhDocente").value.trim();
  const grupo = document.getElementById("bhGrupo").value.trim();
  if (periodo) params.append("periodo", periodo);
  if (dia) params.append("dia", dia);
  if (docenteCedula) params.append("docente_cedula", docenteCedula);
  if (grupo) params.append("grupo", grupo);
  params.append("offset", "0");
  params.append("limit", "200");

  try {
    const data = await apiFetch(`/admin/horarios?${params.toString()}`);
    horariosCacheAdmin = data;
    renderHorariosAdmin(data);
  } catch (err) {
    alert("Error: " + err.message);
  }
}

function renderHorariosAdmin(filas) {
  const tbody = document.getElementById("tbodyHorariosAdmin");
  tbody.innerHTML = "";
  if (!filas.length) {
    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:#999;">Sin resultados</td></tr>';
    return;
  }
  filas.forEach((h, i) => {
    const tr = document.createElement("tr");
    const hora = h.hora_inicio && h.hora_fin ? `${h.hora_inicio} - ${h.hora_fin}` : "";
    tr.innerHTML = `<td>${h.periodo || ""}</td><td>${h.dia || ""}</td><td>${hora}</td><td>${h.grupo || ""}</td><td>${h.asignatura || ""}</td><td>${h.nombre_docente || ""}</td><td>${h.nombre_salon || ""}</td>
      <td>
        <button class="secundario" onclick="abrirEdicionHorario(${i})">Editar</button>
        <button class="secundario" onclick="eliminarHorario(${h.id})">Eliminar</button>
      </td>`;
    tbody.appendChild(tr);
  });
}

function abrirNuevoHorario() {
  idHorarioEnEdicion = null;
  document.getElementById("tituloFormHorario").textContent = "Nuevo horario";
  [
    "hId", "hPeriodo", "hCodigoAsignatura", "hFacultad", "hPrograma", "hPlan", "hAsignatura",
    "hCiclo", "hCreditos", "hGrupo", "hCodigoMoodle", "hCodigoTeams", "hEnlaceTeams", "hEstado",
    "hModalidad", "hJornada", "hCapacidad", "hDia", "hHoraInicio", "hHoraFin", "hNombreSalon",
    "hSede", "hDocenteCedula", "hNombreDocente", "hCorreoDocente", "hObservaciones",
  ].forEach((id) => { document.getElementById(id).value = ""; });
  document.getElementById("formHorarioAdmin").classList.remove("oculto");
  document.getElementById("formHorarioAdmin").scrollIntoView({ behavior: "smooth", block: "center" });
}

function abrirEdicionHorario(indice) {
  const h = horariosCacheAdmin[indice];
  if (!h) return;
  idHorarioEnEdicion = h.id;
  document.getElementById("tituloFormHorario").textContent = `Editar horario #${h.id}`;
  document.getElementById("hId").value = h.id;
  document.getElementById("hPeriodo").value = h.periodo || "";
  document.getElementById("hCodigoAsignatura").value = h.codigo_asignatura || "";
  document.getElementById("hFacultad").value = h.facultad || "";
  document.getElementById("hPrograma").value = h.programa || "";
  document.getElementById("hPlan").value = h.plan || "";
  document.getElementById("hAsignatura").value = h.asignatura || "";
  document.getElementById("hCiclo").value = h.ciclo || "";
  document.getElementById("hCreditos").value = h.creditos || "";
  document.getElementById("hGrupo").value = h.grupo || "";
  document.getElementById("hCodigoMoodle").value = h.codigo_moodle || "";
  document.getElementById("hCodigoTeams").value = h.codigo_teams || "";
  document.getElementById("hEnlaceTeams").value = h.enlace_teams || "";
  document.getElementById("hEstado").value = h.estado || "";
  document.getElementById("hModalidad").value = h.modalidad || "";
  document.getElementById("hJornada").value = h.jornada || "";
  document.getElementById("hCapacidad").value = h.capacidad || "";
  document.getElementById("hDia").value = h.dia || "";
  document.getElementById("hHoraInicio").value = h.hora_inicio ? h.hora_inicio.slice(0, 5) : "";
  document.getElementById("hHoraFin").value = h.hora_fin ? h.hora_fin.slice(0, 5) : "";
  document.getElementById("hNombreSalon").value = h.nombre_salon || "";
  document.getElementById("hSede").value = h.sede || "";
  document.getElementById("hDocenteCedula").value = h.docente_cedula || "";
  document.getElementById("hNombreDocente").value = h.nombre_docente || "";
  document.getElementById("hCorreoDocente").value = h.correo_docente || "";
  document.getElementById("hObservaciones").value = h.observaciones || "";
  document.getElementById("formHorarioAdmin").classList.remove("oculto");
  document.getElementById("formHorarioAdmin").scrollIntoView({ behavior: "smooth", block: "center" });
}

function cancelarFormHorario() {
  document.getElementById("formHorarioAdmin").classList.add("oculto");
  idHorarioEnEdicion = null;
}

async function guardarHorario() {
  const valor = (id) => {
    const v = document.getElementById(id).value.trim();
    return v === "" ? null : v;
  };
  const valorNum = (id) => {
    const v = document.getElementById(id).value.trim();
    return v === "" ? null : Number(v);
  };

  const payload = {
    periodo: valor("hPeriodo"),
    codigo_asignatura: valor("hCodigoAsignatura"),
    facultad: valor("hFacultad"),
    programa: valor("hPrograma"),
    plan: valor("hPlan"),
    asignatura: valor("hAsignatura"),
    ciclo: valor("hCiclo"),
    creditos: valor("hCreditos"),
    grupo: valor("hGrupo"),
    codigo_moodle: valor("hCodigoMoodle"),
    codigo_teams: valor("hCodigoTeams"),
    enlace_teams: valor("hEnlaceTeams"),
    estado: valor("hEstado"),
    modalidad: valor("hModalidad"),
    jornada: valor("hJornada"),
    capacidad: valorNum("hCapacidad"),
    dia: valor("hDia"),
    hora_inicio: valor("hHoraInicio"),
    hora_fin: valor("hHoraFin"),
    nombre_salon: valor("hNombreSalon"),
    sede: valor("hSede"),
    docente_cedula: valorNum("hDocenteCedula"),
    nombre_docente: valor("hNombreDocente"),
    correo_docente: valor("hCorreoDocente"),
    observaciones: valor("hObservaciones"),
  };

  if (!payload.periodo || !payload.grupo) {
    alert("Período y grupo son obligatorios");
    return;
  }

  try {
    if (idHorarioEnEdicion) {
      await apiFetch(`/admin/horarios/${idHorarioEnEdicion}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    } else {
      await apiFetch(`/admin/horarios`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    }
    cancelarFormHorario();
    buscarHorariosAdmin();
  } catch (err) {
    alert("Error: " + err.message);
  }
}

async function eliminarHorario(id) {
  if (!confirm("¿Seguro que deseas eliminar este horario? Esta acción no se puede deshacer.")) return;
  try {
    await apiFetch(`/admin/horarios/${id}`, { method: "DELETE" });
    buscarHorariosAdmin();
  } catch (err) {
    alert("Error: " + err.message);
  }
}

// ---- Inscripciones ----
let inscripcionesCacheAdmin = [];
let idInscripcionEnEdicion = null;

async function buscarInscripcionesAdmin() {
  const params = new URLSearchParams();
  const estudianteCedula = document.getElementById("biEstudiante").value.trim();
  const periodo = document.getElementById("biPeriodo").value.trim();
  if (estudianteCedula) params.append("estudiante_cedula", estudianteCedula);
  if (periodo) params.append("periodo", periodo);
  params.append("offset", "0");
  params.append("limit", "200");

  try {
    const data = await apiFetch(`/admin/inscripciones?${params.toString()}`);
    inscripcionesCacheAdmin = data;
    renderInscripcionesAdmin(data);
  } catch (err) {
    alert("Error: " + err.message);
  }
}

function renderInscripcionesAdmin(filas) {
  const tbody = document.getElementById("tbodyInscripcionesAdmin");
  tbody.innerHTML = "";
  if (!filas.length) {
    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:#999;">Sin resultados</td></tr>';
    return;
  }
  filas.forEach((ins, i) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${ins.estudiante_cedula || ""}</td><td>${ins.periodo || ""}</td><td>${ins.cod_asignatura || ""}</td><td>${ins.asignatura || ""}</td><td>${ins.grupo || ""}</td><td>${ins.jornada || ""}</td><td>${ins.estado || ""}</td>
      <td>
        <button class="secundario" onclick="abrirEdicionInscripcion(${i})">Editar</button>
        <button class="secundario" onclick="eliminarInscripcion(${ins.id})">Eliminar</button>
      </td>`;
    tbody.appendChild(tr);
  });
}

function abrirNuevaInscripcion() {
  idInscripcionEnEdicion = null;
  document.getElementById("tituloFormInscripcion").textContent = "Nueva inscripción";
  [
    "iId", "iEstudianteCedula", "iPeriodo", "iCicloIngreso", "iCodPlan", "iNomPlan",
    "iCodAsignatura", "iAsignatura", "iCiclo", "iCreditos", "iGrupo", "iJornada", "iEstado",
    "iSede", "iIdentificador", "iFlgVirtual", "iNombreFacultad", "iSemilla",
  ].forEach((id) => { document.getElementById(id).value = ""; });
  document.getElementById("formInscripcionAdmin").classList.remove("oculto");
  document.getElementById("formInscripcionAdmin").scrollIntoView({ behavior: "smooth", block: "center" });
}

function abrirEdicionInscripcion(indice) {
  const ins = inscripcionesCacheAdmin[indice];
  if (!ins) return;
  idInscripcionEnEdicion = ins.id;
  document.getElementById("tituloFormInscripcion").textContent = `Editar inscripción #${ins.id}`;
  document.getElementById("iId").value = ins.id;
  document.getElementById("iEstudianteCedula").value = ins.estudiante_cedula || "";
  document.getElementById("iPeriodo").value = ins.periodo || "";
  document.getElementById("iCicloIngreso").value = ins.ciclo_ingreso || "";
  document.getElementById("iCodPlan").value = ins.cod_plan || "";
  document.getElementById("iNomPlan").value = ins.nom_plan || "";
  document.getElementById("iCodAsignatura").value = ins.cod_asignatura || "";
  document.getElementById("iAsignatura").value = ins.asignatura || "";
  document.getElementById("iCiclo").value = ins.ciclo || "";
  document.getElementById("iCreditos").value = ins.creditos || "";
  document.getElementById("iGrupo").value = ins.grupo || "";
  document.getElementById("iJornada").value = ins.jornada || "";
  document.getElementById("iEstado").value = ins.estado || "";
  document.getElementById("iSede").value = ins.sede || "";
  document.getElementById("iIdentificador").value = ins.identificador || "";
  document.getElementById("iFlgVirtual").value = ins.flg_virtual || "";
  document.getElementById("iNombreFacultad").value = ins.nombre_facultad || "";
  document.getElementById("iSemilla").value = ins.semilla || "";
  document.getElementById("formInscripcionAdmin").classList.remove("oculto");
  document.getElementById("formInscripcionAdmin").scrollIntoView({ behavior: "smooth", block: "center" });
}

function cancelarFormInscripcion() {
  document.getElementById("formInscripcionAdmin").classList.add("oculto");
  idInscripcionEnEdicion = null;
}

async function guardarInscripcion() {
  const valor = (id) => {
    const v = document.getElementById(id).value.trim();
    return v === "" ? null : v;
  };

  const payload = {
    estudiante_cedula: valor("iEstudianteCedula"),
    periodo: valor("iPeriodo"),
    ciclo_ingreso: valor("iCicloIngreso"),
    cod_plan: valor("iCodPlan"),
    nom_plan: valor("iNomPlan"),
    cod_asignatura: valor("iCodAsignatura"),
    asignatura: valor("iAsignatura"),
    ciclo: valor("iCiclo"),
    creditos: valor("iCreditos"),
    grupo: valor("iGrupo"),
    jornada: valor("iJornada"),
    estado: valor("iEstado"),
    sede: valor("iSede"),
    identificador: valor("iIdentificador"),
    flg_virtual: valor("iFlgVirtual"),
    nombre_facultad: valor("iNombreFacultad"),
    semilla: valor("iSemilla"),
  };

  if (!payload.estudiante_cedula || !payload.periodo) {
    alert("Cédula del estudiante y período son obligatorios");
    return;
  }

  try {
    if (idInscripcionEnEdicion) {
      await apiFetch(`/admin/inscripciones/${idInscripcionEnEdicion}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    } else {
      await apiFetch(`/admin/inscripciones`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    }
    cancelarFormInscripcion();
    buscarInscripcionesAdmin();
  } catch (err) {
    alert("Error: " + err.message);
  }
}

async function eliminarInscripcion(id) {
  if (!confirm("¿Seguro que deseas eliminar esta inscripción? Esta acción no se puede deshacer.")) return;
  try {
    await apiFetch(`/admin/inscripciones/${id}`, { method: "DELETE" });
    buscarInscripcionesAdmin();
  } catch (err) {
    alert("Error: " + err.message);
  }
}
