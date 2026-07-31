"""
Servicio de importación de los archivos Excel institucionales:
  - PLANEACIÓN (hojas: PLANEACION, DOCENTES, REFLEJOS, CERRADOS)
  - INSCRITOS_POR_CICLO (hoja única con estudiantes matriculados)

Este módulo NO asume nombres de archivo fijos: solo depende de los
encabezados de columna, que se detectan de forma flexible (mayúsculas/
minúsculas, espacios extra, tildes).
"""
import re
import unicodedata
from datetime import time as dtime
from io import BytesIO
from typing import Optional

import openpyxl
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert

from .. import models

SEDES_CONOCIDAS = [
    "SUR", "NORTE", "CENTRO", "CALLE 73", "CALLE 72", "CHAPINERO",
    "OCCIDENTE", "SOACHA", "KENNEDY", "VIRTUAL",
]


def _norm(s) -> str:
    """Normaliza un encabezado: sin tildes, minúsculas, sin espacios extra."""
    if s is None:
        return ""
    s = str(s).strip().upper()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"\s+", " ", s)
    return s


def _header_map(header_row) -> dict:
    """Devuelve {nombre_normalizado: indice_columna} para una fila de encabezado."""
    mapping = {}
    for idx, val in enumerate(header_row):
        key = _norm(val)
        if key:
            mapping[key] = idx
    return mapping


def _get(row, mapping, *names, default=None):
    for name in names:
        idx = mapping.get(_norm(name))
        if idx is not None and idx < len(row):
            value = row[idx]
            if value is not None and str(value).strip() != "":
                return value
    return default


def _to_int(value) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(float(str(value).strip()))
    except (ValueError, TypeError):
        return None


def _to_str(value) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None


def _to_time(value) -> Optional[dtime]:
    if value is None or value == "":
        return None
    if isinstance(value, dtime):
        return value
    s = str(value).strip()
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            from datetime import datetime as _dt
            return _dt.strptime(s, fmt).time()
        except ValueError:
            continue
    return None


def _extraer_sede(nombre_salon: Optional[str], modalidad: Optional[str]) -> Optional[str]:
    """La sede real a veces viene como sufijo de NOMBRE_SALON ('SALON 403-SEDE SUR')
    y en otras filas queda registrada en la columna MODALIDAD por costumbre de captura
    del archivo institucional. Se intenta extraer de ambas fuentes."""
    for text in (nombre_salon, modalidad):
        if not text:
            continue
        t = _norm(text)
        m = re.search(r"SEDE\s+([A-Z0-9 ]+)", t)
        if m:
            return m.group(1).strip().title()
        for sede in SEDES_CONOCIDAS:
            if sede in t:
                return sede.title()
    return None


def _find_header_row(ws, must_contain, max_scan: int = 20):
    """Busca la fila de encabezado escaneando las primeras `max_scan` filas.

    `must_contain` es una lista donde cada elemento puede ser:
      - un nombre de columna (str), o
      - un grupo de nombres alternativos/sinónimos (list[str]), del cual
        basta que aparezca UNO en el encabezado (útil para hojas como
        REFLEJOS que renombran ASIGNATURA/GRUPO como "... VIGENTE").
    """
    grupos = [([m] if isinstance(m, str) else list(m)) for m in must_contain]
    grupos_norm = [[_norm(alias) for alias in grupo] for grupo in grupos]

    for i, row in enumerate(ws.iter_rows(min_row=1, max_row=max_scan, values_only=True)):
        norm_row = [_norm(v) for v in row]
        if all(any(alias == v for v in norm_row for alias in grupo) for grupo in grupos_norm):
            return i + 1, row  # openpyxl es 1-indexado
    raise ValueError(
        f"No se encontró la fila de encabezado esperada (se buscaban las columnas: {must_contain})"
    )


def import_docentes_desde_planeacion(db: Session, wb, carga_id: int) -> tuple[int, int]:
    """Importa/actualiza la hoja DOCENTES (NIT_CC, NOMBRE_COMPLETO, CORREO, FACULTAD, SEDE)."""
    if "DOCENTES" not in wb.sheetnames:
        return 0, 0
    ws = wb["DOCENTES"]
    header_row_num, header_row = _find_header_row(ws, ["NIT_CC", "NOMBRE_COMPLETO"])
    mapping = _header_map(header_row)

    procesadas, errores = 0, 0
    for row in ws.iter_rows(min_row=header_row_num + 1, values_only=True):
        if row is None or all(v is None for v in row):
            continue
        try:
            cedula = _to_int(_get(row, mapping, "NIT_CC"))
            nombre = _to_str(_get(row, mapping, "NOMBRE_COMPLETO"))
            if not cedula or not nombre:
                continue
            correo = _to_str(_get(row, mapping, "CORREO INSTITUCIONAL", "CORREO_INSTITUCIONAL"))
            facultad = _to_str(_get(row, mapping, "FACULTAD"))
            sede = _to_str(_get(row, mapping, "SEDE"))
            if facultad and facultad.upper() in ("#N/A", "N/A"):
                facultad = None
            if sede and sede.upper() in ("#N/A", "N/A"):
                sede = None

            stmt = pg_insert(models.Docente).values(
                cedula=cedula,
                nombre_completo=nombre,
                correo_institucional=correo,
                facultad=facultad,
                sede=sede,
            ).on_conflict_do_update(
                index_elements=["cedula"],
                set_=dict(
                    nombre_completo=nombre,
                    correo_institucional=correo,
                    facultad=facultad,
                    sede=sede,
                ),
            )
            db.execute(stmt)
            procesadas += 1
        except Exception:
            errores += 1
    db.commit()
    return procesadas, errores


def import_horarios_desde_planeacion(
    db: Session, wb, periodo: str, carga_id: int, hoja: str = "PLANEACION"
) -> tuple[int, int]:
    """Importa la hoja de horarios (PLANEACION, REFLEJOS o CERRADOS)."""
    if hoja not in wb.sheetnames:
        return 0, 0
    ws = wb[hoja]
    # La hoja REFLEJOS usa nombres de columna distintos ("... VIGENTE") para
    # la asignatura y el grupo que realmente se dicta; se aceptan como alias.
    header_row_num, header_row = _find_header_row(
        ws, [["ASIGNATURA", "ASIGNATURA VIGENTE"], ["GRUPO", "GRUPO ASIGNATURA VIGENTE"]]
    )
    mapping = _header_map(header_row)

    # Aseguramos que los docentes referenciados existan (aunque no vengan en la
    # hoja DOCENTES) para no romper la llave foránea.
    docentes_vistos = {}

    procesadas, errores = 0, 0
    for row in ws.iter_rows(min_row=header_row_num + 1, values_only=True):
        if row is None or all(v is None for v in row):
            continue
        try:
            llave = _to_str(_get(row, mapping, "LLAVE"))
            grupo = _to_str(_get(row, mapping, "GRUPO", "GRUPO ASIGNATURA VIGENTE"))
            if not grupo:
                continue

            docente_cedula = _to_int(_get(row, mapping, "DOCUMENTO_DOCENTE"))
            if docente_cedula is not None and docente_cedula <= 0:
                # Algunas filas traen 0 como marcador de "docente sin asignar";
                # se trata como ausencia de docente para no violar la llave foránea.
                docente_cedula = None
            nombre_docente = _to_str(_get(row, mapping, "NOMBRE_DOCENTE"))
            correo_docente = _to_str(_get(row, mapping, "CORREO INSTITUCIONAL", "CORREO_INSTITUCIONAL"))

            if docente_cedula is not None and docente_cedula not in docentes_vistos:
                stmt = pg_insert(models.Docente).values(
                    cedula=docente_cedula,
                    nombre_completo=nombre_docente or f"Docente {docente_cedula}",
                    correo_institucional=correo_docente,
                ).on_conflict_do_nothing(index_elements=["cedula"])
                db.execute(stmt)
                docentes_vistos[docente_cedula] = True

            nombre_salon = _to_str(_get(row, mapping, "NOMBRE_SALON"))
            modalidad = _to_str(_get(row, mapping, "MODALIDAD"))
            sede = _extraer_sede(nombre_salon, modalidad)

            horario = models.Horario(
                llave=llave,
                periodo=periodo,
                codigo_asignatura=_to_str(_get(row, mapping, "CODIGO", "CODIGO ASIGNATURA VIGENTE")),
                facultad=_to_str(_get(row, mapping, "FACULTAD")),
                programa=_to_str(_get(row, mapping, "PROGRAMA", "PROGRAMA ASIGNATURA VIGENTE")),
                plan=_to_str(_get(row, mapping, "PLAN")),
                asignatura=_to_str(_get(row, mapping, "ASIGNATURA", "ASIGNATURA VIGENTE")),
                ciclo=_to_str(_get(row, mapping, "CICLO", "CICLO ASIGNATURA VIGENTE")),
                creditos=_to_str(_get(row, mapping, "CREDITOS", "NUMERO DE CREDITOS ASIGNATURA VIGENTE")),
                grupo=grupo,
                codigo_moodle=_to_str(_get(row, mapping, "CODIGO MOODLE")),
                codigo_teams=_to_str(_get(row, mapping, "CODIGO TEAMS")),
                enlace_teams=_to_str(_get(row, mapping, "ENLACE TEAMS")),
                estado=_to_str(_get(row, mapping, "ESTADO")),
                modalidad=modalidad,
                jornada=_to_str(_get(row, mapping, "JORNADA")),
                capacidad=_to_int(_get(row, mapping, "CAPACIDAD")),
                dia=_to_str(_get(row, mapping, "DIA")),
                hora_inicio=_to_time(_get(row, mapping, "H_INICIO")),
                hora_fin=_to_time(_get(row, mapping, "H_FIN")),
                nombre_salon=nombre_salon,
                sede=sede,
                docente_cedula=docente_cedula,
                nombre_docente=nombre_docente,
                correo_docente=correo_docente,
                observaciones=_to_str(_get(row, mapping, "OBSERVACIONES")),
                origen_hoja=hoja,
                carga_id=carga_id,
            )
            db.add(horario)
            procesadas += 1
        except Exception:
            errores += 1
    db.commit()
    return procesadas, errores


def importar_planeacion(db: Session, file_bytes: bytes, periodo: str, carga_id: int) -> dict:
    wb = openpyxl.load_workbook(BytesIO(file_bytes), data_only=True)
    total_ok, total_err = 0, 0

    ok, err = import_docentes_desde_planeacion(db, wb, carga_id)
    total_ok += ok
    total_err += err

    for hoja in ("PLANEACION", "REFLEJOS", "CERRADOS"):
        ok, err = import_horarios_desde_planeacion(db, wb, periodo, carga_id, hoja=hoja)
        total_ok += ok
        total_err += err

    return {"filas_procesadas": total_ok, "filas_error": total_err}


def importar_inscritos(db: Session, file_bytes: bytes, periodo: str, carga_id: int) -> dict:
    """Importa el archivo INSCRITOS_POR_CICLO (hoja única, con filas de título
    antes del encabezado real)."""
    wb = openpyxl.load_workbook(BytesIO(file_bytes), data_only=True)
    ws = wb[wb.sheetnames[0]]
    header_row_num, header_row = _find_header_row(ws, ["IDENTIFICACION", "GRUPO", "ASIGNATURA"])
    mapping = _header_map(header_row)

    procesadas, errores = 0, 0
    estudiantes_vistos = set()

    for row in ws.iter_rows(min_row=header_row_num + 1, values_only=True):
        if row is None or all(v is None for v in row):
            continue
        try:
            cedula = _to_str(_get(row, mapping, "IDENTIFICACION"))
            if not cedula:
                continue

            if cedula not in estudiantes_vistos:
                stmt = pg_insert(models.Estudiante).values(
                    cedula=cedula,
                    tipo=_to_str(_get(row, mapping, "TIPO")),
                    nombres=_to_str(_get(row, mapping, "NOMBRES")),
                    apellidos=_to_str(_get(row, mapping, "APELLIDOS")),
                    correo_aula_virtual=_to_str(_get(row, mapping, "CORREO AULA VIRTUAL")),
                    email=_to_str(_get(row, mapping, "EMAIL")),
                    celular=_to_str(_get(row, mapping, "CELULAR")),
                    telefono=_to_str(_get(row, mapping, "TELEFONO")),
                    ciclo_ingreso=_to_str(_get(row, mapping, "CICLO_INGRESO")),
                ).on_conflict_do_update(
                    index_elements=["cedula"],
                    set_=dict(
                        tipo=_to_str(_get(row, mapping, "TIPO")),
                        nombres=_to_str(_get(row, mapping, "NOMBRES")),
                        apellidos=_to_str(_get(row, mapping, "APELLIDOS")),
                        correo_aula_virtual=_to_str(_get(row, mapping, "CORREO AULA VIRTUAL")),
                        email=_to_str(_get(row, mapping, "EMAIL")),
                        celular=_to_str(_get(row, mapping, "CELULAR")),
                        telefono=_to_str(_get(row, mapping, "TELEFONO")),
                        ciclo_ingreso=_to_str(_get(row, mapping, "CICLO_INGRESO")),
                    ),
                )
                db.execute(stmt)
                estudiantes_vistos.add(cedula)

            inscripcion_stmt = pg_insert(models.Inscripcion).values(
                estudiante_cedula=cedula,
                periodo=periodo,
                ciclo_ingreso=_to_str(_get(row, mapping, "CICLO_INGRESO")),
                cod_plan=_to_str(_get(row, mapping, "COD_PLAN")),
                nom_plan=_to_str(_get(row, mapping, "NOM_PLAN")),
                cod_asignatura=_to_str(_get(row, mapping, "COD_ASIGNATURA")),
                asignatura=_to_str(_get(row, mapping, "ASIGNATURA")),
                ciclo=_to_str(_get(row, mapping, "CICLO")),
                creditos=_to_str(_get(row, mapping, "CREDITOS")),
                grupo=_to_str(_get(row, mapping, "GRUPO")),
                jornada=_to_str(_get(row, mapping, "JORNADA")),
                estado=_to_str(_get(row, mapping, "ESTADO")),
                sede=_to_str(_get(row, mapping, "SEDE")),
                identificador=_to_str(_get(row, mapping, "IDENTIFICADOR")),
                flg_virtual=_to_str(_get(row, mapping, "FLG_VIRTUAL")),
                nombre_facultad=_to_str(_get(row, mapping, "NOMBRE_FACULTAD")),
                semilla=_to_str(_get(row, mapping, "SEMILLA")),
                carga_id=carga_id,
            ).on_conflict_do_update(
                index_elements=["estudiante_cedula", "periodo", "cod_asignatura", "grupo"],
                set_=dict(
                    estado=_to_str(_get(row, mapping, "ESTADO")),
                    jornada=_to_str(_get(row, mapping, "JORNADA")),
                    sede=_to_str(_get(row, mapping, "SEDE")),
                    carga_id=carga_id,
                ),
            )
            db.execute(inscripcion_stmt)
            procesadas += 1
        except Exception:
            errores += 1

    db.commit()
    return {"filas_procesadas": procesadas, "filas_error": errores}
