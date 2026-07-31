from typing import Optional, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user, aplicar_alcance_coordinador

router = APIRouter(prefix="/api/horarios", tags=["horarios"])


@router.get("", response_model=List[schemas.HorarioOut])
def consultar_horarios(
    dia: Optional[str] = Query(None, description="Ej: '1. LUNES'"),
    sede: Optional[str] = None,
    salon: Optional[str] = None,
    materia: Optional[str] = None,
    grupo: Optional[str] = None,
    docente_cedula: Optional[int] = None,
    docente_nombre: Optional[str] = None,
    periodo: Optional[str] = None,
    facultad: Optional[str] = None,
    programa: Optional[str] = None,
    jornada: Optional[str] = None,
    limit: int = Query(500, le=2000),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user),
):
    """Consulta de horarios con los filtros solicitados: día, sede, salón,
    materia y grupo de formación (además de docente y período)."""
    q = db.query(models.Horario)
    if dia:
        q = q.filter(models.Horario.dia.ilike(f"%{dia}%"))
    if sede:
        q = q.filter(models.Horario.sede.ilike(f"%{sede}%"))
    if salon:
        q = q.filter(models.Horario.nombre_salon.ilike(f"%{salon}%"))
    if materia:
        q = q.filter(models.Horario.asignatura.ilike(f"%{materia}%"))
    if grupo:
        q = q.filter(models.Horario.grupo.ilike(f"%{grupo}%"))
    if docente_cedula:
        q = q.filter(models.Horario.docente_cedula == docente_cedula)
    if docente_nombre:
        q = q.filter(models.Horario.nombre_docente.ilike(f"%{docente_nombre}%"))
    if periodo:
        q = q.filter(models.Horario.periodo == periodo)
    if facultad:
        q = q.filter(models.Horario.facultad.ilike(f"%{facultad}%"))
    if programa:
        q = q.filter(models.Horario.programa.ilike(f"%{programa}%"))
    if jornada:
        q = q.filter(models.Horario.jornada.ilike(f"%{jornada}%"))

    q = aplicar_alcance_coordinador(q, current_user, models.Horario.facultad, models.Horario.sede)

    q = q.order_by(models.Horario.dia, models.Horario.hora_inicio)
    return q.limit(limit).all()


@router.get("/filtros", tags=["horarios"])
def opciones_de_filtro(
    periodo: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user),
):
    """Devuelve los valores distintos disponibles para poblar los combos del
    formulario de consulta (día, sede, salón, materia, grupo, período)."""
    base = db.query(models.Horario)
    if periodo:
        base = base.filter(models.Horario.periodo == periodo)
    base = aplicar_alcance_coordinador(base, current_user, models.Horario.facultad, models.Horario.sede)

    def distinct_values(column):
        rows = base.with_entities(column).filter(column.isnot(None)).distinct().all()
        return sorted({r[0] for r in rows if r[0]})

    return {
        "dias": distinct_values(models.Horario.dia),
        "sedes": distinct_values(models.Horario.sede),
        "salones": distinct_values(models.Horario.nombre_salon),
        "materias": distinct_values(models.Horario.asignatura),
        "grupos": distinct_values(models.Horario.grupo),
        "facultades": distinct_values(models.Horario.facultad),
        "programas": distinct_values(models.Horario.programa),
        "jornadas": distinct_values(models.Horario.jornada),
        "periodos": sorted({r[0] for r in db.query(models.Horario.periodo).distinct().all() if r[0]}),
    }


@router.get("/choques", tags=["horarios"])
def detectar_choques(
    periodo: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user),
):
    """Utilidad extra: detecta posibles choques de horario -- mismo docente o
    mismo salón, mismo día y franjas de hora que se solapan."""
    q = db.query(models.Horario)
    if periodo:
        q = q.filter(models.Horario.periodo == periodo)
    registros = q.filter(models.Horario.dia.isnot(None)).all()

    def solapan(a, b):
        if not (a.hora_inicio and a.hora_fin and b.hora_inicio and b.hora_fin):
            return False
        return a.hora_inicio < b.hora_fin and b.hora_inicio < a.hora_fin

    choques = []
    por_dia = {}
    for r in registros:
        por_dia.setdefault(r.dia, []).append(r)

    for dia, lista in por_dia.items():
        for i in range(len(lista)):
            for j in range(i + 1, len(lista)):
                a, b = lista[i], lista[j]
                if not solapan(a, b):
                    continue
                if a.docente_cedula and a.docente_cedula == b.docente_cedula:
                    choques.append({
                        "tipo": "docente",
                        "dia": dia,
                        "docente": a.nombre_docente,
                        "horario_1": {"grupo": a.grupo, "asignatura": a.asignatura, "inicio": str(a.hora_inicio), "fin": str(a.hora_fin)},
                        "horario_2": {"grupo": b.grupo, "asignatura": b.asignatura, "inicio": str(b.hora_inicio), "fin": str(b.hora_fin)},
                    })
                if a.nombre_salon and a.nombre_salon == b.nombre_salon:
                    choques.append({
                        "tipo": "salon",
                        "dia": dia,
                        "salon": a.nombre_salon,
                        "horario_1": {"grupo": a.grupo, "asignatura": a.asignatura, "inicio": str(a.hora_inicio), "fin": str(a.hora_fin)},
                        "horario_2": {"grupo": b.grupo, "asignatura": b.asignatura, "inicio": str(b.hora_inicio), "fin": str(b.hora_fin)},
                    })
    return {"total_choques": len(choques), "choques": choques[:200]}
