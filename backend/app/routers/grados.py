from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import dentro_del_alcance, get_current_user, require_roles
from ..services.auditoria import registrar

router = APIRouter(prefix="/api/grados", tags=["asistencia a grados"])

ADMIN_EVENTOS = require_roles("admin", "administrador", "bienestar_universitario")
GESTION_ASISTENCIA = require_roles(
    "admin", "administrador", "bienestar_universitario", "coordinador"
)
CONSULTA_GRADOS = require_roles(
    "admin", "administrador", "bienestar_universitario", "decano", "coordinador"
)


def _exigir_alcance(usuario, facultad, programa):
    if not dentro_del_alcance(usuario, facultad, programa):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El registro está fuera de tu facultad o programa autorizado.",
        )


@router.get("/ceremonias", response_model=List[schemas.CeremoniaOut])
def listar_ceremonias(
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(CONSULTA_GRADOS),
):
    query = db.query(models.CeremoniaGrado)
    if usuario.rol in ("decano", "coordinador"):
        if usuario.rol == "decano" and not usuario.facultad_alcance:
            return []
        if usuario.rol == "coordinador" and not (
            usuario.facultad_alcance or usuario.sede_alcance
        ):
            return []
        if usuario.facultad_alcance:
            query = query.filter(
                models.CeremoniaGrado.facultad.ilike(f"%{usuario.facultad_alcance}%")
            )
        if usuario.sede_alcance:
            query = query.filter(
                models.CeremoniaGrado.programa.ilike(f"%{usuario.sede_alcance}%")
            )
    return query.order_by(models.CeremoniaGrado.fecha.desc()).all()


@router.post("/ceremonias", response_model=schemas.CeremoniaOut, status_code=201)
def crear_ceremonia(
    datos: schemas.CeremoniaCreate,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(ADMIN_EVENTOS),
):
    if not datos.nombre.strip() or not datos.lugar.strip():
        raise HTTPException(status_code=422, detail="Nombre y lugar son obligatorios.")
    ceremonia = models.CeremoniaGrado(
        **datos.model_dump(), creado_por_id=usuario.id
    )
    db.add(ceremonia)
    db.flush()
    registrar(db, "crear", "ceremonia_grado", usuario, ceremonia.id)
    db.commit()
    db.refresh(ceremonia)
    return ceremonia


@router.get("/ceremonias/{ceremonia_id}/graduandos", response_model=List[schemas.GraduandoOut])
def listar_graduandos(
    ceremonia_id: int,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(CONSULTA_GRADOS),
):
    query = db.query(models.GraduandoCeremonia).filter(
        models.GraduandoCeremonia.ceremonia_id == ceremonia_id
    )
    if usuario.rol in ("decano", "coordinador"):
        if usuario.rol == "decano" and not usuario.facultad_alcance:
            return []
        if usuario.rol == "coordinador" and not (
            usuario.facultad_alcance or usuario.sede_alcance
        ):
            return []
        if usuario.facultad_alcance:
            query = query.filter(
                models.GraduandoCeremonia.facultad.ilike(f"%{usuario.facultad_alcance}%")
            )
        if usuario.sede_alcance:
            query = query.filter(
                models.GraduandoCeremonia.programa.ilike(f"%{usuario.sede_alcance}%")
            )
    return query.order_by(models.GraduandoCeremonia.id).all()


@router.post("/ceremonias/{ceremonia_id}/graduandos", response_model=schemas.GraduandoOut, status_code=201)
def agregar_graduando(
    ceremonia_id: int,
    datos: schemas.GraduandoCreate,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(GESTION_ASISTENCIA),
):
    _exigir_alcance(usuario, datos.facultad, datos.programa)
    if not db.get(models.CeremoniaGrado, ceremonia_id):
        raise HTTPException(status_code=404, detail="Ceremonia no encontrada.")
    if not db.get(models.Estudiante, datos.estudiante_cedula):
        raise HTTPException(status_code=404, detail="El estudiante no existe en SIIHAPI.")
    graduando = models.GraduandoCeremonia(
        ceremonia_id=ceremonia_id,
        creado_por_id=usuario.id,
        **datos.model_dump(),
    )
    db.add(graduando)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="El estudiante ya está inscrito en la ceremonia.")
    registrar(db, "crear", "graduando_ceremonia", usuario, graduando.id)
    db.commit()
    db.refresh(graduando)
    return graduando


@router.patch("/graduandos/{graduando_id}/validar", response_model=schemas.GraduandoOut)
def validar_graduando(
    graduando_id: int,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(require_roles("admin", "administrador", "decano")),
):
    graduando = db.get(models.GraduandoCeremonia, graduando_id)
    if not graduando:
        raise HTTPException(status_code=404, detail="Graduando no encontrado.")
    _exigir_alcance(usuario, graduando.facultad, graduando.programa)
    graduando.validado = True
    registrar(db, "validar", "graduando_ceremonia", usuario, graduando.id)
    db.commit()
    db.refresh(graduando)
    return graduando


@router.post("/asistencias", response_model=schemas.AsistenciaOut)
def registrar_asistencia(
    datos: schemas.AsistenciaCreate,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(GESTION_ASISTENCIA),
):
    graduando = db.query(models.GraduandoCeremonia).filter(
        models.GraduandoCeremonia.id == datos.graduando_id
    ).with_for_update().first()
    if not graduando:
        raise HTTPException(status_code=404, detail="Graduando no encontrado.")
    _exigir_alcance(usuario, graduando.facultad, graduando.programa)
    asistencia = db.query(models.AsistenciaGrado).filter(
        models.AsistenciaGrado.graduando_id == graduando.id
    ).first()
    accion = "actualizar" if asistencia else "registrar"
    if asistencia:
        asistencia.presente = datos.presente
        asistencia.observacion = datos.observacion
        asistencia.registrado_por_id = usuario.id
        asistencia.actualizado_en = func.now()
    else:
        asistencia = models.AsistenciaGrado(
            **datos.model_dump(), registrado_por_id=usuario.id
        )
        db.add(asistencia)
    db.flush()
    registrar(db, accion, "asistencia_grado", usuario, asistencia.id, {
        "graduando_id": graduando.id, "presente": datos.presente
    })
    db.commit()
    db.refresh(asistencia)
    return asistencia


@router.get("/ceremonias/{ceremonia_id}/reporte")
def reporte(
    ceremonia_id: int,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(CONSULTA_GRADOS),
):
    graduandos = listar_graduandos(ceremonia_id, db, usuario)
    ids = [item.id for item in graduandos]
    presentes = 0
    if ids:
        presentes = db.query(models.AsistenciaGrado).filter(
            models.AsistenciaGrado.graduando_id.in_(ids),
            models.AsistenciaGrado.presente.is_(True),
        ).count()
    return {
        "ceremonia_id": ceremonia_id,
        "total_graduandos": len(ids),
        "presentes": presentes,
        "pendientes": len(ids) - presentes,
    }
