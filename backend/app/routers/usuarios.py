from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import require_admin
from ..security import hash_password
from ..services.auditoria import registrar

router = APIRouter(prefix="/api/usuarios", tags=["usuarios"])


@router.get("", response_model=List[schemas.UsuarioOut])
def listar_usuarios(
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_admin),
):
    """Solo el administrador puede ver y gestionar la lista de usuarios."""
    return db.query(models.Usuario).order_by(models.Usuario.username).all()


@router.post("", response_model=schemas.UsuarioOut)
def crear_usuario(
    datos: schemas.UsuarioCreate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_admin),
):
    existente = db.query(models.Usuario).filter(models.Usuario.username == datos.username).first()
    if existente:
        raise HTTPException(status_code=400, detail="Ese nombre de usuario ya existe.")
    roles_validos = (
        "admin", "administrador", "bienestar_universitario", "decano",
        "consulta", "coordinador", "docente", "consulta_estudiante",
    )
    if datos.rol not in roles_validos:
        raise HTTPException(
            status_code=400,
            detail=f"El rol debe ser uno de: {', '.join(roles_validos)}.",
        )
    if datos.rol == "coordinador" and not (datos.facultad_alcance or datos.sede_alcance):
        raise HTTPException(
            status_code=400,
            detail="Un coordinador debe tener al menos una facultad o sede de alcance asignada.",
        )
    if len(datos.password) < 12:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 12 caracteres.")
    if datos.rol == "decano" and not datos.facultad_alcance:
        raise HTTPException(status_code=400, detail="Un decano debe tener una facultad asignada.")

    usuario = models.Usuario(
        username=datos.username,
        password_hash=hash_password(datos.password),
        nombre_completo=datos.nombre_completo,
        rol=datos.rol,
        cedula_relacionada=datos.cedula_relacionada,
        facultad_alcance=datos.facultad_alcance if datos.rol in ("coordinador", "decano") else None,
        sede_alcance=datos.sede_alcance if datos.rol == "coordinador" else None,
    )
    db.add(usuario)
    db.flush()
    registrar(db, "crear", "usuario", current_user, usuario.id, {"rol": usuario.rol})
    db.commit()
    db.refresh(usuario)
    return usuario


@router.patch("/{usuario_id}/estado", response_model=schemas.UsuarioOut)
def cambiar_estado_usuario(
    usuario_id: int,
    activo: bool,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_admin),
):
    usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    usuario.activo = activo
    registrar(db, "cambiar_estado", "usuario", current_user, usuario.id, {"activo": activo})
    db.commit()
    db.refresh(usuario)
    return usuario
