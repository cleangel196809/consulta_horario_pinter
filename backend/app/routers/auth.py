from datetime import datetime, timedelta, timezone
from threading import Lock
from time import monotonic

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..security import (
    verify_password,
    create_access_token,
    hash_password,
    generar_reset_token,
    RESET_TOKEN_EXPIRE_MINUTES,
)
from ..deps import get_current_user
from ..services.notificaciones import enviar_correo_reset_password
from ..services.auditoria import registrar

router = APIRouter(prefix="/api/auth", tags=["autenticacion"])

_failed_attempts = {}
_failed_attempts_lock = Lock()
LOGIN_WINDOW_SECONDS = 300
LOGIN_MAX_ATTEMPTS = 10
LOGIN_MAX_CLIENTS = 10000


def _login_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _prune_attempts_locked(now: float):
    for client, timestamps in list(_failed_attempts.items()):
        active = [
            timestamp for timestamp in timestamps
            if now - timestamp < LOGIN_WINDOW_SECONDS
        ]
        if active:
            _failed_attempts[client] = active
        else:
            _failed_attempts.pop(client, None)


def _reserve_login_attempt(key: str):
    now = monotonic()
    with _failed_attempts_lock:
        _prune_attempts_locked(now)
        attempts = _failed_attempts.get(key, [])
        if len(attempts) >= LOGIN_MAX_ATTEMPTS:
            return False, len(attempts)
        if key not in _failed_attempts and len(_failed_attempts) >= LOGIN_MAX_CLIENTS:
            return False, 0
        attempts.append(now)
        _failed_attempts[key] = attempts
        return True, len(attempts)


@router.post("/login", response_model=schemas.TokenResponse)
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    key = _login_key(request)
    allowed, attempt_count = _reserve_login_attempt(key)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiados intentos. Espera unos minutos antes de volver a intentar.",
        )
    user = db.query(models.Usuario).filter(models.Usuario.username == form_data.username).first()
    if not user or not user.activo or not verify_password(form_data.password, user.password_hash):
        if user and attempt_count == 1:
            registrar(db, "login_fallido", "sesion", user)
            db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos.",
        )
    with _failed_attempts_lock:
        _failed_attempts.pop(key, None)
    token = create_access_token({"sub": user.username, "rol": user.rol})
    registrar(db, "login_exitoso", "sesion", user)
    db.commit()
    return schemas.TokenResponse(
        access_token=token,
        rol=user.rol,
        nombre_completo=user.nombre_completo,
        username=user.username,
        debe_cambiar_password=bool(user.debe_cambiar_password),
    )


@router.get("/me", response_model=schemas.UsuarioOut)
def me(current_user: models.Usuario = Depends(get_current_user)):
    return current_user


@router.post("/cambiar-password")
def cambiar_password(
    datos: schemas.CambiarPasswordRequest,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user),
):
    """Permite a cualquier usuario autenticado cambiar su propia contraseña.
    Se usa tanto para el cambio voluntario como para el cambio forzado en el
    primer ingreso (cuando `debe_cambiar_password=True`, ver login)."""
    if not verify_password(datos.password_actual, current_user.password_hash):
        raise HTTPException(status_code=400, detail="La contraseña actual no es correcta.")
    if not datos.password_nueva or len(datos.password_nueva) < 12:
        raise HTTPException(
            status_code=400, detail="La nueva contraseña debe tener al menos 12 caracteres."
        )
    current_user.password_hash = hash_password(datos.password_nueva)
    current_user.debe_cambiar_password = False
    registrar(db, "cambiar_password", "usuario", current_user, current_user.id)
    db.add(current_user)
    db.commit()
    return {"detail": "Contraseña actualizada correctamente."}


@router.post("/olvide-password")
def olvide_password(
    datos: schemas.OlvidePasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Inicia el flujo de "olvidé mi contraseña". Por seguridad, SIEMPRE
    responde el mismo mensaje genérico exista o no ese usuario (para no
    revelar qué nombres de usuario están registrados). Solo puede enviarse
    el enlace si el `username` es un correo (es el caso de docentes y
    estudiantes, y de cualquier admin/consulta/coordinador cuyo usuario se
    haya creado con su correo); cuentas como "admin" que no son un correo
    no pueden auto-recuperarse por este medio y deben reiniciarse desde
    otra cuenta admin en el panel de usuarios."""
    mensaje_generico = (
        "Si el usuario existe y tiene un correo asociado, se envió un enlace "
        "para restablecer la contraseña."
    )
    username = (datos.username or "").strip()
    user = db.query(models.Usuario).filter(models.Usuario.username == username).first()

    if user and user.activo and "@" in username:
        user.reset_token = generar_reset_token()
        user.reset_token_expira = datetime.now(timezone.utc) + timedelta(
            minutes=RESET_TOKEN_EXPIRE_MINUTES
        )
        db.add(user)
        db.commit()
        link = f"{str(request.base_url).rstrip('/')}/reset-password.html?token={user.reset_token}"
        try:
            enviar_correo_reset_password(username, user.nombre_completo, link)
        except Exception:
            # No se le informa al usuario si el envío de correo falló (mismo
            # mensaje genérico), para no filtrar si la cuenta existe.
            pass

    return {"detail": mensaje_generico}


@router.post("/restablecer-password")
def restablecer_password(
    datos: schemas.RestablecerPasswordRequest,
    db: Session = Depends(get_db),
):
    """Segundo paso del flujo de "olvidé mi contraseña": consume el token
    del enlace enviado por correo y define la nueva contraseña."""
    if not datos.token:
        raise HTTPException(status_code=400, detail="Falta el token de recuperación.")
    if not datos.password_nueva or len(datos.password_nueva) < 12:
        raise HTTPException(
            status_code=400, detail="La nueva contraseña debe tener al menos 12 caracteres."
        )

    user = db.query(models.Usuario).filter(models.Usuario.reset_token == datos.token).first()
    ahora = datetime.now(timezone.utc)
    expira = user.reset_token_expira if user else None
    if expira is not None and expira.tzinfo is None:
        # Postgres puede devolver el datetime sin tzinfo (columna TIMESTAMP
        # sin zona); se asume UTC, que es como se guardó arriba.
        expira = expira.replace(tzinfo=timezone.utc)

    if not user or not expira or expira < ahora:
        raise HTTPException(
            status_code=400,
            detail="El enlace de recuperación no es válido o ya expiró. Solicita uno nuevo.",
        )

    user.password_hash = hash_password(datos.password_nueva)
    user.debe_cambiar_password = False
    user.reset_token = None
    user.reset_token_expira = None
    registrar(db, "restablecer_password", "usuario", user, user.id)
    db.add(user)
    db.commit()
    return {"detail": "Contraseña actualizada correctamente. Ya puedes iniciar sesión."}
