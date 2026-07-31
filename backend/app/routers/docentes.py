from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user

router = APIRouter(prefix="/api/docentes", tags=["docentes"])


@router.get("", response_model=List[schemas.DocenteOut])
def listar_docentes(
    q: Optional[str] = Query(None, description="Busca por nombre o cédula"),
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user),
):
    query = db.query(models.Docente)
    if q:
        if q.isdigit():
            query = query.filter(models.Docente.cedula == int(q))
        else:
            query = query.filter(models.Docente.nombre_completo.ilike(f"%{q}%"))
    return query.order_by(models.Docente.nombre_completo).limit(limit).all()


@router.get("/{cedula}", response_model=schemas.DocenteOut)
def obtener_docente(
    cedula: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user),
):
    docente = db.query(models.Docente).filter(models.Docente.cedula == cedula).first()
    if not docente:
        raise HTTPException(status_code=404, detail="Docente no encontrado")
    return docente


@router.get("/{cedula}/horario", response_model=List[schemas.HorarioOut])
def horario_del_docente(
    cedula: int,
    periodo: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user),
):
    q = db.query(models.Horario).filter(models.Horario.docente_cedula == cedula)
    if periodo:
        q = q.filter(models.Horario.periodo == periodo)
    return q.order_by(models.Horario.dia, models.Horario.hora_inicio).all()
