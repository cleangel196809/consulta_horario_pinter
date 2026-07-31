exigirSesion();
document.getElementById("nombreUsuario").textContent = getNombreUsuario();
document.getElementById("badgeRol").textContent = getRol() === "admin" ? "Administrador" : "Consulta";

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
      tr.innerHTML = `<td>${fecha}</td><td>${c.tipo}</td><td>${c.nombre_archivo || ""}</td><td>${c.periodo || ""}</td><td>${c.filas_procesadas}</td><td>${c.filas_error}</td><td>${c.estado}</td>`;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error(err);
  }
}

async function cargarUsuarios() {
  try {
    const data = await apiFetch("/usuarios");
    const tbody = document.getElementById("tbodyUsuarios");
    tbody.innerHTML = "";
    data.forEach((u) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td>${u.username}</td><td>${u.nombre_completo || ""}</td><td>${u.rol}</td><td>${u.activo ? "Sí" : "No"}</td>
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

  if (!username || !password) {
    alert("Usuario y contraseña son obligatorios");
    return;
  }

  try {
    await apiFetch("/usuarios", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password, nombre_completo, rol }),
    });
    document.getElementById("nuevoUsername").value = "";
    document.getElementById("nuevoPassword").value = "";
    document.getElementById("nuevoNombre").value = "";
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
