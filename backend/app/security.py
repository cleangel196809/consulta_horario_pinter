import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import jwt, JWTError
from passlib.context import CryptContext

from .config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# bcrypt es intencionalmente lento (~250-300ms por hash con el costo por
# defecto): eso está bien para un login manual, pero se vuelve impracticable
# cuando se crean miles de cuentas de golpe (una por cada estudiante/docente
# nuevo al importar un Excel de INSCRITOS con miles de filas) — con 5.000
# estudiantes nuevos, 300ms cada uno son ~25 minutos solo en hashing, y eso
# fue justamente lo que hacía parecer "colgada" la carga en Render. Para ese
# caso puntual (la contraseña inicial es la cédula, un dato no secreto, y se
# fuerza su cambio en el primer ingreso vía `debe_cambiar_password`) se usa
# un costo de bcrypt mucho menor: sigue siendo un hash real (nunca texto
# plano en la base de datos), solo que computacionalmente más barato.
pwd_context_bulk = CryptContext(schemes=["bcrypt"], bcrypt__rounds=4)

# Cuánto tiempo es válido un token de "olvidé mi contraseña" antes de expirar.
RESET_TOKEN_EXPIRE_MINUTES = 30


def generar_reset_token() -> str:
    """Token de un solo uso para el flujo de recuperación de contraseña.
    No es un JWT a propósito: se guarda tal cual en la base de datos y se
    invalida (se borra) apenas se usa, así no hace falta una lista de
    revocación."""
    return secrets.token_urlsafe(32)


def hash_password(password: str, bulk: bool = False) -> str:
    """`bulk=True` usa un costo de bcrypt mucho menor (ver `pwd_context_bulk`
    arriba) — pensado SOLO para la creación masiva de cuentas automáticas de
    docentes/estudiantes durante la importación de Excel. El costo de bcrypt
    queda codificado dentro del propio hash, así que `verify_password`
    funciona igual sin importar con qué costo se generó."""
    ctx = pwd_context_bulk if bulk else pwd_context
    return ctx.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_minutes: Optional[int] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or settings.access_token_expire_minutes
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError:
        return None
