"""
CRUD administrativo de horarios e inscripciones, para poder corregir a mano
datos puntuales sin tener que recargar todo el archivo Excel. Todos los
endpoints están protegidos con `require_admin` (mismo criterio que
`admin_upload.py`).
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import require_admin

router = APIRouter(prefix="/api/admin", tags=["administracion-crud"])


# ---------------------------------------------------------------------
# Horarios
# ---------------------------------------------------------------------
@router.get("/horarios", response_model=List[schemas.HorarioOut])
def listar_horarios_admin(
    periodo: Optional[str] = None,
    dia: Optional[str] = None,
    docente_cedula: Optional[int] = None,
    grupo: Optional[str] = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, le=2000),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_admin),
):
    """Lista paginada de horarios con filtros básicos, pensada para el
    panel de administración (a diferencia de `GET /api/horarios`, que es la
    consulta pública de solo lectura)."""
    q = db.query(models.Horario)
    if periodo:
        q = q.filter(models.Horario.periodo == periodo)
    if dia:
        q = q.filter(models.Horario.dia.ilike(f"%{dia}%"))
    if docente_cedula:
        q = q.filter(models.Horario.docente_cedula == docente_cedula)
    if grupo:
        q = q.filter(models.Horario.grupo.ilike(f"%{grupo}%"))
    q = q.order_by(models.Horario.periodo.desc(), models.Horario.dia, models.Horario.hora_inicio)
    return q.offset(offset).limit(limit).all()


@router.post("/horarios", response_model=schemas.HorarioOut)
def crear_horario_admin(
    datos: schemas.HorarioCreate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_admin),
):
    horario = models.Horario(**datos.model_dump(), origen_hoja="MANUAL")
    db.add(horario)
    db.commit()
    db.refresh(horario)
    return horario


@router.put("/horarios/{horario_id}", response_model=schemas.HorarioOut)
def actualizar_horario_admin(
    horario_id: int,
    datos: schemas.HorarioUpdate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_admin),
):
    horario = db.query(models.Horario).filter(models.Horario.id == horario_id).first()
    if not horario:
        raise HTTPException(status_code=404, detail="Horario no encontrado")
    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(horario, campo, valor)
    db.commit()
    db.refresh(horario)
    return horario


@router.delete("/horarios/{horario_id}")
def eliminar_horario_admin(
    horario_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_admin),
):
    horario = db.query(models.Horario).filter(models.Horario.id == horario_id).first()
    if not horario:
        raise HTTPException(status_code=404, detail="Horario no encontrado")
    db.delete(horario)
    db.commit()
    return {"detail": "Horario eliminado correctamente."}


# ---------------------------------------------------------------------
# Inscripciones
# ---------------------------------------------------------------------
@router.get("/inscripciones", response_model=List[schemas.InscripcionOut])
def listar_inscripciones_admin(
    estudiante_cedula: Optional[str] = None,
    periodo: Optional[str] = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, le=2000),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_admin),
):
    q = db.query(models.Inscripcion)
    if estudiante_cedula:
        q = q.filter(models.Inscripcion.estudiante_cedula == estudiante_cedula)
    if periodo:
        q = q.filter(models.Inscripcion.periodo == periodo)
    q = q.order_by(models.Inscripcion.periodo.desc(), models.Inscripcion.estudiante_cedula)
    return q.offset(offset).limit(limit).all()


@router.post("/inscripciones", response_model=schemas.InscripcionOut)
def crear_inscripcion_admin(
    datos: schemas.InscripcionCreate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_admin),
):
    estudiante = db.query(models.Estudiante).filter(
        models.Estudiante.cedula == datos.estudiante_cedula
    ).first()
    if not estudiante:
        raise HTTPException(
            status_code=400,
            detail="No existe un estudiante con esa cédula; créalo primero o corrige el dato.",
        )
    inscripcion = models.Inscripcion(**datos.model_dump())
    db.add(inscripcion)
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"No se pudo crear la inscripción: {exc}")
    db.refresh(inscripcion)
    return inscripcion


@router.put("/inscripciones/{inscripcion_id}", response_model=schemas.InscripcionOut)
def actualizar_inscripcion_admin(
    inscripcion_id: int,
    datos: schemas.InscripcionUpdate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_admin),
):
    inscripcion = db.query(models.Inscripcion).filter(models.Inscripcion.id == inscripcion_id).first()
    if not inscripcion:
        raise HTTPException(status_code=404, detail="Inscripción no encontrada")
    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(inscripcion, campo, valor)
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"No se pudo actualizar la inscripción: {exc}")
    db.refresh(inscripcion)
    return inscripcion


@router.delete("/inscripciones/{inscripcion_id}")
def eliminar_inscripcion_admin(
    inscripcion_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_admin),
):
    inscripcion = db.query(models.Inscripcion).filter(models.Inscripcion.id == inscripcion_id).first()
    if not inscripcion:
        raise HTTPException(status_code=404, detail="Inscripción no encontrada")
    db.delete(inscripcion)
    db.commit()
    return {"detail": "Inscripción eliminada correctamente."}
