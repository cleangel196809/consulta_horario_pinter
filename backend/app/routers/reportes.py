"""
Reportes y utilidades de análisis sobre los horarios cargados:
- Dashboard de indicadores generales.
- Carga horaria semanal por docente (con alerta de sobrecarga).
- Comparador entre dos periodos/ciclos.
- Detección de inconsistencias entre PLANEACION, REFLEJOS y CERRADOS.
"""
from collections import defaultdict
from datetime import time as dtime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..deps import get_current_user, aplicar_alcance_coordinador

router = APIRouter(prefix="/api/reportes", tags=["reportes"])

# Umbral de horas semanales a partir del cual se marca "sobrecarga" a un docente.
HORAS_SOBRECARGA = 22


def _horas(hi: Optional[dtime], hf: Optional[dtime]) -> float:
    if not hi or not hf:
        return 0.0
    minutos = (hf.hour * 60 + hf.minute) - (hi.hour * 60 + hi.minute)
    return max(minutos, 0) / 60


@router.get("/dashboard")
def dashboard(
    periodo: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user),
):
    base = db.query(models.Horario)
    if periodo:
        base = base.filter(models.Horario.periodo == periodo)
    base = aplicar_alcance_coordinador(base, current_user, models.Horario.facultad, models.Horario.sede)

    grupos_por_origen = dict(
        base.with_entities(models.Horario.origen_hoja, func.count(func.distinct(models.Horario.grupo)))
        .group_by(models.Horario.origen_hoja).all()
    )

    matriculados_q = db.query(models.Inscripcion)
    if periodo:
        matriculados_q = matriculados_q.filter(models.Inscripcion.periodo == periodo)

    def top(columna, limite=15):
        rows = (
            matriculados_q.with_entities(columna, func.count(models.Inscripcion.id))
            .filter(columna.isnot(None))
            .group_by(columna)
            .order_by(func.count(models.Inscripcion.id).desc())
            .limit(limite)
            .all()
        )
        return [{"nombre": r[0], "total": r[1]} for r in rows]

    ocupacion_rows = (
        base.with_entities(models.Horario.hora_inicio, models.Horario.hora_fin, func.count(models.Horario.id))
        .filter(models.Horario.hora_inicio.isnot(None))
        .group_by(models.Horario.hora_inicio, models.Horario.hora_fin)
        .order_by(models.Horario.hora_inicio)
        .all()
    )
    ocupacion = [
        {"franja": f"{hi} - {hf}", "total_clases": total}
        for hi, hf, total in ocupacion_rows
    ]

    return {
        "periodo": periodo,
        "grupos_por_origen": {
            "planeacion": grupos_por_origen.get("PLANEACION", 0),
            "reflejos": grupos_por_origen.get("REFLEJOS", 0),
            "cerrados": grupos_por_origen.get("CERRADOS", 0),
        },
        "matriculados_por_programa": top(models.Inscripcion.nom_plan),
        "matriculados_por_sede": top(models.Inscripcion.sede),
        "matriculados_por_jornada": top(models.Inscripcion.jornada),
        "ocupacion_salones_por_franja": ocupacion,
        "total_docentes": db.query(models.Docente).count(),
        "total_estudiantes": db.query(models.Estudiante).count(),
    }


@router.get("/carga-horaria-docentes")
# Nota sobre deduplicación de PLANEACIÓN (services/excel_import.py): la
# eliminación de filas duplicadas al cargar usa como clave
# docente_cedula + dia + hora_inicio + hora_fin + nombre_salon + grupo +
# asignatura. Como `dia` forma parte de la clave, una misma clase que
# legítimamente se repite en días distintos (p. ej. lunes y miércoles)
# NUNCA se identifica como duplicada ni se elimina por error: cada día
# genera una clave distinta y por lo tanto una fila distinta en `horarios`,
# así que el cálculo de horas/semana de abajo (que suma _horas() por cada
# fila) sigue sumando correctamente todas las franjas reales del docente.
# La deduplicación solo mejora este cálculo al quitar filas que eran copias
# exactas (mismo día y misma franja) que antes inflaban el conteo de horas.
def carga_horaria_docentes(
    periodo: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user),
):
    q = db.query(models.Horario).filter(models.Horario.docente_cedula.isnot(None))
    if periodo:
        q = q.filter(models.Horario.periodo == periodo)
    q = aplicar_alcance_coordinador(q, current_user, models.Horario.facultad, models.Horario.sede)

    por_docente = defaultdict(lambda: {"horas": 0.0, "clases": 0, "nombre": None})
    for h in q.all():
        info = por_docente[h.docente_cedula]
        info["horas"] += _horas(h.hora_inicio, h.hora_fin)
        info["clases"] += 1
        info["nombre"] = h.nombre_docente

    resultado = [
        {
            "docente_cedula": cedula,
            "nombre_docente": info["nombre"],
            "horas_semana": round(info["horas"], 1),
            "clases_semana": info["clases"],
            "sobrecarga": info["horas"] > HORAS_SOBRECARGA,
        }
        for cedula, info in por_docente.items()
    ]
    resultado.sort(key=lambda x: x["horas_semana"], reverse=True)
    return {"umbral_sobrecarga_horas": HORAS_SOBRECARGA, "docentes": resultado}


@router.get("/comparar-periodos")
def comparar_periodos(
    periodo_a: str,
    periodo_b: str,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user),
):
    def snapshot(periodo):
        q = db.query(models.Horario).filter(models.Horario.periodo == periodo)
        q = aplicar_alcance_coordinador(q, current_user, models.Horario.facultad, models.Horario.sede)
        datos = {}
        for h in q.all():
            datos[h.grupo] = {
                "asignatura": h.asignatura,
                "docente": h.nombre_docente,
                "docente_cedula": h.docente_cedula,
                "salon": h.nombre_salon,
                "dia": h.dia,
                "hora_inicio": str(h.hora_inicio) if h.hora_inicio else None,
            }
        return datos

    snap_a = snapshot(periodo_a)
    snap_b = snapshot(periodo_b)

    solo_en_a = sorted(set(snap_a) - set(snap_b))
    solo_en_b = sorted(set(snap_b) - set(snap_a))
    cambios = []
    for grupo in sorted(set(snap_a) & set(snap_b)):
        a, b = snap_a[grupo], snap_b[grupo]
        diffs = {k: {"antes": a[k], "despues": b[k]} for k in a if a[k] != b[k]}
        if diffs:
            cambios.append({"grupo": grupo, "cambios": diffs})

    return {
        "periodo_a": periodo_a,
        "periodo_b": periodo_b,
        "grupos_solo_en_a": solo_en_a,
        "grupos_solo_en_b": solo_en_b,
        "grupos_con_cambios": cambios,
        "resumen": {
            "eliminados": len(solo_en_a),
            "nuevos": len(solo_en_b),
            "modificados": len(cambios),
        },
    }


@router.get("/inconsistencias")
def inconsistencias(
    periodo: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user),
):
    q = db.query(models.Horario)
    if periodo:
        q = q.filter(models.Horario.periodo == periodo)
    q = aplicar_alcance_coordinador(q, current_user, models.Horario.facultad, models.Horario.sede)
    registros = q.all()

    grupos_activos = {h.grupo for h in registros if h.origen_hoja in ("PLANEACION", "REFLEJOS") and h.dia}
    grupos_cerrados = {h.grupo for h in registros if h.origen_hoja == "CERRADOS"}
    grupos_reflejos = {h.grupo for h in registros if h.origen_hoja == "REFLEJOS"}
    grupos_planeacion = {h.grupo for h in registros if h.origen_hoja == "PLANEACION"}

    cerrados_pero_activos = sorted(grupos_cerrados & grupos_activos)
    reflejos_sin_vigente = sorted(grupos_reflejos - grupos_planeacion)

    return {
        "periodo": periodo,
        "grupos_cerrados_con_horario_activo": cerrados_pero_activos,
        "total_cerrados_con_horario_activo": len(cerrados_pero_activos),
        "reflejos_sin_grupo_vigente_en_planeacion": reflejos_sin_vigente,
        "total_reflejos_sin_vigente": len(reflejos_sin_vigente),
    }
