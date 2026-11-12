import getpass
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import models
from app.database import Base, SessionLocal, engine
from app.migrations import run_migrations
from app.security import hash_password


def main():
    username = input("Usuario administrador: ").strip()
    password = getpass.getpass("Contraseña (mínimo 12 caracteres): ")
    if not username or len(password) < 12:
        raise SystemExit("Usuario obligatorio y contraseña de mínimo 12 caracteres.")
    Base.metadata.create_all(bind=engine)
    run_migrations()
    with SessionLocal() as db:
        if db.query(models.Usuario).filter(models.Usuario.username == username).first():
            raise SystemExit("El usuario ya existe.")
        db.add(models.Usuario(
            username=username,
            password_hash=hash_password(password),
            nombre_completo="Administrador",
            rol="administrador",
        ))
        db.commit()
    print("Administrador creado correctamente.")


if __name__ == "__main__":
    main()
