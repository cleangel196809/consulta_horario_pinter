from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user

router = APIRouter(prefix="/api/estudiantes", tags=["estudiantes"])


@router.get("", response_model=List[schemas.EstudianteOut])
def listar_estudiantes(
    q: Optional[str] = Query(None, description="Busca por nombre, apellido o cédula"),
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user),
):
    query = db.query(models.Estudiante)
    if q:
        query = query.filter(
            (models.Estudiante.cedula.ilike(f"%{q}%"))
            | (models.Estudiante.nombres.ilike(f"%{q}%"))
            | (models.Estudiante.apellidos.ilike(f"%{q}%"))
        )
    return query.order_by(models.Estudiante.apellidos).limit(limit).all()


@router.get("/{cedula}", response_model=schemas.EstudianteOut)
def obtener_estudiante(
    cedula: str,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user),
):
    estudiante = db.query(models.Estudiante).filter(models.Estudiante.cedula == cedula).first()
    if not estudiante:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    return estudiante


@router.get("/{cedula}/horario", response_model=List[schemas.HorarioOut])
def horario_del_estudiante(
    cedula: str,
    periodo: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user),
):
    """El horario de un estudiante se arma cruzando sus inscripciones
    (por grupo y período) contra la tabla de horarios."""
    insc_q = db.query(models.Inscripcion).filter(models.Inscripcion.estudiante_cedula == cedula)
    if periodo:
        insc_q = insc_q.filter(models.Inscripcion.periodo == periodo)
    grupos = {i.grupo for i in insc_q.all() if i.grupo}
    if not grupos:
        return []

    q = db.query(models.Horario).filter(models.Horario.grupo.in_(grupos))
    if periodo:
        q = q.filter(models.Horario.periodo == periodo)
    return q.order_by(models.Horario.dia, models.Horario.hora_inicio).all()
