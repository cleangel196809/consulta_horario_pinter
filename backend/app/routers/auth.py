from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..security import verify_password, create_access_token, hash_password
from ..deps import get_current_user

router = APIRouter(prefix="/api/auth", tags=["autenticacion"])


@router.post("/login", response_model=schemas.TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.Usuario).filter(models.Usuario.username == form_data.username).first()
    if not user or not user.activo or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos.",
        )
    token = create_access_token({"sub": user.username, "rol": user.rol})
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
    if not datos.password_nueva or len(datos.password_nueva) < 4:
        raise HTTPException(
            status_code=400, detail="La nueva contraseña debe tener al menos 4 caracteres."
        )
    current_user.password_hash = hash_password(datos.password_nueva)
    current_user.debe_cambiar_password = False
    db.add(current_user)
    db.commit()
    return {"detail": "Contraseña actualizada correctamente."}
