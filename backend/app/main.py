import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .database import Base, engine, SessionLocal
from . import models
from .config import settings
from .security import hash_password
from .routers import auth, horarios, docentes, estudiantes, admin_upload, usuarios, exportar, reportes


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

        # Usuario de solo-consulta de demostración, para probar el rol sin
        # privilegios de administrador apenas se levanta la aplicación.
        existe_prueba = db.query(models.Usuario).filter(
            models.Usuario.username == settings.test_username
        ).first()
        if not existe_prueba:
            prueba = models.Usuario(
                username=settings.test_username,
                password_hash=hash_password(settings.test_password),
                nombre_completo="Usuario de prueba (consulta)",
                rol="consulta",
            )
            db.add(prueba)
            db.commit()
            print(f"[init] Usuario de prueba '{settings.test_username}' (rol consulta) creado.")

        # Usuario de prueba con rol "coordinador", limitado a una facultad,
        # para poder probar el alcance filtrado sin tener que crearlo a mano
        # desde el panel admin.
        existe_coord = db.query(models.Usuario).filter(
            models.Usuario.username == settings.coord_username
        ).first()
        if not existe_coord:
            coord = models.Usuario(
                username=settings.coord_username,
                password_hash=hash_password(settings.coord_password),
                nombre_completo="Usuario de prueba (coordinador)",
                rol="coordinador",
                facultad_alcance=settings.coord_facultad_alcance,
            )
            db.add(coord)
            db.commit()
            print(
                f"[init] Usuario de prueba '{settings.coord_username}' "
                f"(rol coordinador, facultad '{settings.coord_facultad_alcance}') creado."
            )
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
app.include_router(exportar.router)
app.include_router(reportes.router)


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
