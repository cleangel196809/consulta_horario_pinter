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
    if current_user.rol != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta acción solo puede realizarla un administrador.",
        )
    return current_user


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
