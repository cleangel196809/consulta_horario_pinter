import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from .database import Base, engine, SessionLocal
from . import models
from .config import settings
from .security import hash_password
from .migrations import run_migrations
from .routers import auth, horarios, docentes, estudiantes, admin_upload, admin_crud, usuarios, exportar, reportes, grados


def migrar_columnas_nuevas():
    """`Base.metadata.create_all()` solo crea tablas que no existen: NO le
    agrega columnas nuevas a una tabla que ya existía (por ejemplo, la base
    de datos de una instalación ya desplegada, como la de Render). Este
    bloque es una mini-migración idempotente (se puede correr en cada
    arranque sin problema) para que esas instalaciones existentes reciban
    las columnas agregadas después del primer despliegue."""
    with engine.begin() as conn:
        conn.execute(text(
            "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS reset_token VARCHAR(255)"
        ))
        conn.execute(text(
            "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS reset_token_expira TIMESTAMP"
        ))
        conn.execute(text(
            "ALTER TABLE cargas_archivo ADD COLUMN IF NOT EXISTS duplicados_omitidos INTEGER DEFAULT 0"
        ))


def crear_admin_inicial():
    if not settings.admin_password:
        return
    if len(settings.admin_password) < 12:
        raise RuntimeError("ADMIN_PASSWORD debe tener al menos 12 caracteres.")
    db = SessionLocal()
    try:
        existe = db.query(models.Usuario).filter(
            models.Usuario.rol.in_(("admin", "administrador"))
        ).first()
        if not existe:
            admin = models.Usuario(
                username=settings.admin_username,
                password_hash=hash_password(settings.admin_password),
                nombre_completo="Administrador",
                rol="administrador",
            )
            db.add(admin)
            db.commit()
            print(f"[init] Usuario administrador '{settings.admin_username}' creado.")

    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if len(settings.secret_key) < 32:
        raise RuntimeError("SECRET_KEY debe configurarse con al menos 32 caracteres aleatorios.")
    Base.metadata.create_all(bind=engine)
    run_migrations()
    migrar_columnas_nuevas()
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
    allow_origins=settings.cors_origin_list,
    allow_credentials=bool(settings.cors_origin_list),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(horarios.router)
app.include_router(docentes.router)
app.include_router(estudiantes.router)
app.include_router(admin_upload.router)
app.include_router(admin_crud.router)
app.include_router(usuarios.router)
app.include_router(exportar.router)
app.include_router(reportes.router)
app.include_router(grados.router)


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


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
