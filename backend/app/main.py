import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .database import Base, engine, SessionLocal
from . import models
from .config import settings
from .security import hash_password
from .routers import auth, horarios, docentes, estudiantes, admin_upload, usuarios


def crear_admin_inicial():
    db = SessionLocal()
    try:
        existe = db.query(models.Usuario).filter(models.Usuario.rol == "admin").first()
        if not existe:
            admin = models.Usuario(
                username=settings.admin_username,
                password_hash=hash_password(settings.admin_password),
                nombre_completo="Administrador",
                rol="admin",
            )
            db.add(admin)
            db.commit()
            print(f"[init] Usuario administrador '{settings.admin_username}' creado.")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    crear_admin_inicial()
    yield


app = FastAPI(
    title="Consulta de Horarios PINTER",
    description="API para consultar horarios de docentes y estudiantes, y para "
                 "cargar los archivos de planeación e inscritos (solo administrador).",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(horarios.router)
app.include_router(docentes.router)
app.include_router(estudiantes.router)
app.include_router(admin_upload.router)
app.include_router(usuarios.router)


@app.get("/api/salud", tags=["salud"])
def salud():
    return {"status": "ok"}


# Sirve el frontend estático (login / consulta / admin). La ruta es
# configurable con FRONTEND_DIR para poder ejecutar la API también fuera
# de Docker (donde /app/frontend no existe) sin que falle el arranque.
FRONTEND_DIR = os.environ.get("FRONTEND_DIR", "/app/frontend")
if os.path.isdir(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
else:
    print(f"[aviso] No se montó el frontend: no existe el directorio '{FRONTEND_DIR}'")
