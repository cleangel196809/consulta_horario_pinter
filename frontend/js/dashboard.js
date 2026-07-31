exigirSesion();
document.getElementById("nombreUsuario").textContent = getNombreUsuario();
document.getElementById("badgeRol").textContent = getRol() === "admin" ? "Administrador" : (getRol() === "coordinador" ? "Coordinador" : "Consulta");
if (getRol() === "admin") document.getElementById("tabAdmin").classList.remove("oculto");

let charts = {};

function destruirChart(id) {
  if (charts[id]) { charts[id].destroy(); delete charts[id]; }
}

function colorPalette(n) {
  const base = ["#0b3d91", "#4a86e8", "#16a766", "#ffad46", "#cc3a21", "#8e63ce", "#f691b3", "#2da2bb", "#a46a21", "#653e9b"];
  const out = [];
  for (let i = 0; i < n; i++) out.push(base[i % base.length]);
  return out;
}

async function cargarPeriodos() {
  try {
    const data = await apiFetch("/horarios/filtros");
    const selects = ["fPeriodo", "cmpA", "cmpB"];
    selects.forEach((id) => {
      const sel = document.getElementById(id);
      const placeholder = id === "fPeriodo" ? '<option value="">Todos</option>' : "";
      sel.innerHTML = placeholder + data.periodos.map((p) => `<option value="${p}">${p}</option>`).join("");
    });
  } catch (err) { console.error(err); }
}

async function cargarDashboard(periodo) {
  const data = await apiFetch(`/reportes/dashboard${periodo ? "?periodo=" + encodeURIComponent(periodo) : ""}`);

  destruirChart("grupos");
  charts.grupos = new Chart(document.getElementById("chartGrupos"), {
    type: "doughnut",
    data: {
      labels: ["Planeación (activos)", "Reflejos", "Cerrados"],
      datasets: [{ data: [data.grupos_por_origen.planeacion, data.grupos_por_origen.reflejos, data.grupos_por_origen.cerrados], backgroundColor: colorPalette(3) }],
    },
  });

  destruirChart("ocupacion");
  charts.ocupacion = new Chart(document.getElementById("chartOcupacion"), {
    type: "bar",
    data: {
      labels: data.ocupacion_salones_por_franja.map((f) => f.franja),
      datasets: [{ label: "Clases", data: data.ocupacion_salones_por_franja.map((f) => f.total_clases), backgroundColor: "#4a86e8" }],
    },
    options: { plugins: { legend: { display: false } } },
  });

  destruirChart("programas");
  charts.programas = new Chart(document.getElementById("chartProgramas"), {
    type: "bar",
    data: {
      labels: data.matriculados_por_programa.map((p) => (p.nombre || "").slice(0, 35)),
      datasets: [{ label: "Matriculados", data: data.matriculados_por_programa.map((p) => p.total), backgroundColor: "#16a766" }],
    },
    options: { indexAxis: "y", plugins: { legend: { display: false } } },
  });

  destruirChart("sedejornada");
  charts.sedejornada = new Chart(document.getElementById("chartSedeJornada"), {
    type: "pie",
    data: {
      labels: data.matriculados_por_sede.map((s) => s.nombre),
      datasets: [{ data: data.matriculados_por_sede.map((s) => s.total), backgroundColor: colorPalette(data.matriculados_por_sede.length) }],
    },
  });
}

async function cargarCargaHoraria(periodo) {
  const data = await apiFetch(`/reportes/carga-horaria-docentes${periodo ? "?periodo=" + encodeURIComponent(periodo) : ""}`);
  document.getElementById("umbralSobrecarga").textContent = `umbral: ${data.umbral_sobrecarga_horas}h/semana`;
  const tbody = document.getElementById("tbodyCarga");
  tbody.innerHTML = "";
  data.docentes.slice(0, 50).forEach((d) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${d.nombre_docente || d.docente_cedula}</td><td>${d.horas_semana}</td><td>${d.clases_semana}</td>
      <td>${d.sobrecarga ? '<span class="pill" style="background:#fdecea;color:#b3261e;">Sobrecarga</span>' : '<span class="pill">Normal</span>'}</td>`;
    tbody.appendChild(tr);
  });
}

async function cargarChoques(periodo) {
  const data = await apiFetch(`/horarios/choques${periodo ? "?periodo=" + encodeURIComponent(periodo) : ""}`);
  const tbody = document.getElementById("tbodyChoques");
  tbody.innerHTML = "";
  if (data.choques.length === 0) {
    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:#999;">Sin choques detectados</td></tr>';
    return;
  }
  data.choques.slice(0, 100).forEach((c) => {
    const tr = document.createElement("tr");
    const detalle = c.tipo === "docente" ? (c.docente || "") : (c.salon || "");
    tr.innerHTML = `<td>${c.tipo}</td><td>${c.dia}</td><td>${detalle}</td>
      <td>${c.horario_1.asignatura} (${c.horario_1.grupo})<br>${c.horario_1.inicio}-${c.horario_1.fin}</td>
      <td>${c.horario_2.asignatura} (${c.horario_2.grupo})<br>${c.horario_2.inicio}-${c.horario_2.fin}</td>`;
    tbody.appendChild(tr);
  });
}

async function cargarInconsistencias(periodo) {
  const data = await apiFetch(`/reportes/inconsistencias${periodo ? "?periodo=" + encodeURIComponent(periodo) : ""}`);
  const div = document.getElementById("resumenInconsistencias");
  div.innerHTML = `
    <p><b>${data.total_cerrados_con_horario_activo}</b> grupo(s) marcados como CERRADOS que siguen con horario activo en PLANEACIÓN.</p>
    <p><b>${data.total_reflejos_sin_vigente}</b> reflejo(s) cuya asignatura "vigente" no aparece en PLANEACIÓN.</p>
  `;
}

async function compararPeriodos() {
  const a = document.getElementById("cmpA").value;
  const b = document.getElementById("cmpB").value;
  if (!a || !b) { alert("Selecciona ambos periodos"); return; }
  try {
    const data = await apiFetch(`/reportes/comparar-periodos?periodo_a=${encodeURIComponent(a)}&periodo_b=${encodeURIComponent(b)}`);
    const div = document.getElementById("resultadoComparador");
    div.innerHTML = `
      <p><b>${data.resumen.nuevos}</b> grupo(s) nuevos en ${b}, <b>${data.resumen.eliminados}</b> ya no aparecen, <b>${data.resumen.modificados}</b> con cambios.</p>
      <details><summary>Ver detalle de grupos con cambios (${data.grupos_con_cambios.length})</summary>
        <pre style="white-space:pre-wrap;font-size:0.8rem;">${JSON.stringify(data.grupos_con_cambios.slice(0, 30), null, 2)}</pre>
      </details>
    `;
  } catch (err) {
    alert("Error al comparar: " + err.message);
  }
}

async function cargarTodo() {
  const periodo = document.getElementById("fPeriodo").value;
  await Promise.all([
    cargarDashboard(periodo),
    cargarCargaHoraria(periodo),
    cargarChoques(periodo),
    cargarInconsistencias(periodo),
  ]);
}

cargarPeriodos().then(cargarTodo);
