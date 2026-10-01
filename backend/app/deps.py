from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .database import get_db
from .security import decode_access_token
from . import models

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.Usuario:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar la sesión. Inicia sesión nuevamente.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception
    user = db.query(models.Usuario).filter(models.Usuario.username == username).first()
    if user is None or not user.activo:
        raise credentials_exception
    return user


def require_admin(current_user: models.Usuario = Depends(get_current_user)) -> models.Usuario:
    if current_user.rol not in ("admin", "administrador"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta acción solo puede realizarla un administrador.",
        )
    return current_user


def require_roles(*roles):
    allowed = set(roles)

    def dependency(current_user: models.Usuario = Depends(get_current_user)):
        if current_user.rol not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para realizar esta acción.",
            )
        return current_user

    return dependency


def dentro_del_alcance(current_user: models.Usuario, facultad=None, programa=None) -> bool:
    if current_user.rol in ("admin", "administrador", "bienestar_universitario"):
        return True
    if current_user.rol == "decano" and not current_user.facultad_alcance:
        return False
    if current_user.rol == "coordinador" and not current_user.programa_alcance:
        return False
    if current_user.facultad_alcance and (
        not facultad
        or current_user.facultad_alcance.strip().casefold() != facultad.strip().casefold()
    ):
        return False
    if current_user.programa_alcance and (
        not programa
        or current_user.programa_alcance.strip().casefold() != programa.strip().casefold()
    ):
        return False
    return True


def aplicar_alcance_coordinador(query, current_user: models.Usuario, columna_facultad, columna_sede):
    """Si el usuario tiene rol 'coordinador', restringe automáticamente la
    consulta a su facultad y/o sede asignada, para que solo vea lo que le
    corresponde a su alcance."""
    if current_user.rol == "coordinador":
        if current_user.facultad_alcance:
            query = query.filter(columna_facultad.ilike(f"%{current_user.facultad_alcance}%"))
        if current_user.sede_alcance:
            query = query.filter(columna_sede.ilike(f"%{current_user.sede_alcance}%"))
    return query
