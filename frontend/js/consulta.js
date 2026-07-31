exigirSesion();

document.getElementById("nombreUsuario").textContent = getNombreUsuario();
document.getElementById("badgeRol").textContent = getRol() === "admin" ? "Administrador" : "Consulta";
if (getRol() === "admin") {
  document.getElementById("tabAdmin").classList.remove("oculto");
}

function llenarSelect(id, valores, actual) {
  const sel = document.getElementById(id);
  const primerOpcion = sel.options[0];
  sel.innerHTML = "";
  sel.appendChild(primerOpcion);
  valores.forEach((v) => {
    const opt = document.createElement("option");
    opt.value = v;
    opt.textContent = v;
    if (v === actual) opt.selected = true;
    sel.appendChild(opt);
  });
}

async function cargarFiltros() {
  try {
    const periodo = document.getElementById("fPeriodo").value;
    const data = await apiFetch(`/horarios/filtros${periodo ? "?periodo=" + encodeURIComponent(periodo) : ""}`);
    llenarSelect("fPeriodo", data.periodos, periodo);
    llenarSelect("fDia", data.dias);
    llenarSelect("fSede", data.sedes);
    llenarSelect("fSalon", data.salones);
    llenarSelect("fGrupo", data.grupos);
  } catch (err) {
    console.error(err);
  }
}

async function buscar() {
  const params = new URLSearchParams();
  const campos = {
    periodo: "fPeriodo",
    dia: "fDia",
    sede: "fSede",
    salon: "fSalon",
    materia: "fMateria",
    grupo: "fGrupo",
    docente_nombre: "fDocente",
  };
  for (const [param, idCampo] of Object.entries(campos)) {
    const valor = document.getElementById(idCampo).value.trim();
    if (valor) params.append(param, valor);
  }

  try {
    const data = await apiFetch(`/horarios?${params.toString()}`);
    renderTabla(data);
  } catch (err) {
    alert("Error al consultar horarios: " + err.message);
  }
}

function renderTabla(filas) {
  const tbody = document.getElementById("tbody");
  tbody.innerHTML = "";
  document.getElementById("conteo").textContent = `${filas.length} resultado(s)`;

  if (filas.length === 0) {
    tbody.innerHTML = `<tr><td colspan="9" style="text-align:center;color:#999;">Sin resultados para los filtros seleccionados</td></tr>`;
    return;
  }

  filas.forEach((f) => {
    const tr = document.createElement("tr");
    const hora = (f.hora_inicio || "") && (f.hora_fin || "") ? `${f.hora_inicio} - ${f.hora_fin}` : "";
    tr.innerHTML = `
      <td>${f.dia || ""}</td>
      <td>${hora}</td>
      <td>${f.sede || ""}</td>
      <td>${f.nombre_salon || ""}</td>
      <td>${f.asignatura || ""}</td>
      <td>${f.grupo || ""}</td>
      <td>${f.nombre_docente || ""}</td>
      <td>${f.programa || ""}</td>
      <td>${f.estado || ""}</td>
    `;
    tbody.appendChild(tr);
  });
}

document.getElementById("fPeriodo").addEventListener("change", cargarFiltros);

cargarFiltros().then(buscar);
