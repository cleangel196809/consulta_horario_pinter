from datetime import time, datetime
from typing import Optional
from pydantic import BaseModel


# ---------- Auth ----------
class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    rol: str
    nombre_completo: Optional[str] = None
    username: str


class UsuarioCreate(BaseModel):
    username: str
    password: str
    nombre_completo: Optional[str] = None
    rol: str = "consulta"
    cedula_relacionada: Optional[str] = None
    facultad_alcance: Optional[str] = None
    sede_alcance: Optional[str] = None


class UsuarioOut(BaseModel):
    id: int
    username: str
    nombre_completo: Optional[str]
    rol: str
    facultad_alcance: Optional[str] = None
    sede_alcance: Optional[str] = None
    activo: bool

    class Config:
        from_attributes = True


# ---------- Docentes ----------
class DocenteOut(BaseModel):
    cedula: int
    nombre_completo: str
    correo_institucional: Optional[str] = None
    facultad: Optional[str] = None
    sede: Optional[str] = None

    class Config:
        from_attributes = True


# ---------- Estudiantes ----------
class EstudianteOut(BaseModel):
    cedula: str
    tipo: Optional[str] = None
    nombres: Optional[str] = None
    apellidos: Optional[str] = None
    email: Optional[str] = None
    celular: Optional[str] = None
    ciclo_ingreso: Optional[str] = None

    class Config:
        from_attributes = True


# ---------- Horarios ----------
class HorarioOut(BaseModel):
    id: int
    periodo: str
    facultad: Optional[str] = None
    programa: Optional[str] = None
    asignatura: Optional[str] = None
    grupo: str
    estado: Optional[str] = None
    modalidad: Optional[str] = None
    jornada: Optional[str] = None
    dia: Optional[str] = None
    hora_inicio: Optional[time] = None
    hora_fin: Optional[time] = None
    nombre_salon: Optional[str] = None
    sede: Optional[str] = None
    docente_cedula: Optional[int] = None
    nombre_docente: Optional[str] = None
    correo_docente: Optional[str] = None
    codigo_moodle: Optional[str] = None
    codigo_teams: Optional[str] = None
    enlace_teams: Optional[str] = None
    origen_hoja: Optional[str] = None

    class Config:
        from_attributes = True


# ---------- Cargas ----------
class CargaArchivoOut(BaseModel):
    id: int
    tipo: str
    nombre_archivo: Optional[str]
    periodo: Optional[str]
    filas_procesadas: int
    filas_error: int
    estado: str
    creado_en: Optional[datetime] = None

    class Config:
        from_attributes = True
