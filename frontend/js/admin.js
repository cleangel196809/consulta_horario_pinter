exigirSesion();
document.getElementById("nombreUsuario").textContent = getNombreUsuario();
document.getElementById("badgeRol").textContent =
  getRol() === "admin" ? "Administrador" : (getRol() === "coordinador" ? "Coordinador" : "Consulta");

if (getRol() !== "admin") {
  document.getElementById("contenidoAdmin").innerHTML =
    '<div class="card"><h2>Acceso restringido</h2><p>Esta sección solo está disponible para usuarios con rol de administrador.</p></div>';
} else {
  inicializarAdmin();
}

function inicializarAdmin() {
  document.getElementById("formPlaneacion").addEventListener("submit", async (e) => {
    e.preventDefault();
    await subirArchivo("planeacion", "periodoPlaneacion", "archivoPlaneacion", "msgPlaneacion", "/admin/cargar-planeacion");
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

async function cargarHistorial() {
  try {
    const data = await apiFetch("/admin/cargas");
    const tbody = document.getElementById("tbodyHistorial");
    tbody.innerHTML = "";
    data.forEach((c) => {
      const tr = document.createElement("tr");
      const fecha = c.creado_en ? new Date(c.creado_en).toLocaleString() : "";
      tr.innerHTML = `<td>${fecha}</td><td>${c.tipo}</td><td>${c.nombre_archivo || ""}</td><td>${c.periodo || ""}</td><td>${c.filas_procesadas}</td><td>${c.filas_error}</td><td>${c.estado}</td>
        <td><button class="secundario" onclick="notificarCarga(${c.id})">Notificar</button></td>`;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error(err);
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
