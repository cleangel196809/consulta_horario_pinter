// Utilidades comunes para hablar con la API desde cualquier página.
const API_BASE = "/api";

function getToken() {
  return localStorage.getItem("ph_token");
}

function getRol() {
  return localStorage.getItem("ph_rol");
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
