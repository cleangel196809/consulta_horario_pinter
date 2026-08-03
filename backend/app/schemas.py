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
    # Indica al frontend si debe forzar el flujo de cambio de contraseña
    # antes de dejar usar el resto de la aplicación (login inicial de
    # docentes/estudiantes, cuya clave inicial es su cédula).
    debe_cambiar_password: bool = False


class CambiarPasswordRequest(BaseModel):
    password_actual: str
    password_nueva: str


class OlvidePasswordRequest(BaseModel):
    username: str


class RestablecerPasswordRequest(BaseModel):
    token: str
    password_nueva: str


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
    debe_cambiar_password: bool = False

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


# ---------- Horarios (CRUD admin) ----------
class HorarioCreate(BaseModel):
    periodo: str
    codigo_asignatura: Optional[str] = None
    facultad: Optional[str] = None
    programa: Optional[str] = None
    plan: Optional[str] = None
    asignatura: Optional[str] = None
    ciclo: Optional[str] = None
    creditos: Optional[str] = None
    grupo: str
    codigo_moodle: Optional[str] = None
    codigo_teams: Optional[str] = None
    enlace_teams: Optional[str] = None
    estado: Optional[str] = None
    modalidad: Optional[str] = None
    jornada: Optional[str] = None
    capacidad: Optional[int] = None
    dia: Optional[str] = None
    hora_inicio: Optional[time] = None
    hora_fin: Optional[time] = None
    nombre_salon: Optional[str] = None
    sede: Optional[str] = None
    docente_cedula: Optional[int] = None
    nombre_docente: Optional[str] = None
    correo_docente: Optional[str] = None
    observaciones: Optional[str] = None


class HorarioUpdate(BaseModel):
    """Igual que HorarioCreate pero con todos los campos opcionales, para
    permitir actualizaciones parciales (PUT con los campos que se quieran
    cambiar)."""
    periodo: Optional[str] = None
    codigo_asignatura: Optional[str] = None
    facultad: Optional[str] = None
    programa: Optional[str] = None
    plan: Optional[str] = None
    asignatura: Optional[str] = None
    ciclo: Optional[str] = None
    creditos: Optional[str] = None
    grupo: Optional[str] = None
    codigo_moodle: Optional[str] = None
    codigo_teams: Optional[str] = None
    enlace_teams: Optional[str] = None
    estado: Optional[str] = None
    modalidad: Optional[str] = None
    jornada: Optional[str] = None
    capacidad: Optional[int] = None
    dia: Optional[str] = None
    hora_inicio: Optional[time] = None
    hora_fin: Optional[time] = None
    nombre_salon: Optional[str] = None
    sede: Optional[str] = None
    docente_cedula: Optional[int] = None
    nombre_docente: Optional[str] = None
    correo_docente: Optional[str] = None
    observaciones: Optional[str] = None


# ---------- Inscripciones (CRUD admin) ----------
class InscripcionOut(BaseModel):
    id: int
    estudiante_cedula: str
    periodo: str
    ciclo_ingreso: Optional[str] = None
    cod_plan: Optional[str] = None
    nom_plan: Optional[str] = None
    cod_asignatura: Optional[str] = None
    asignatura: Optional[str] = None
    ciclo: Optional[str] = None
    creditos: Optional[str] = None
    grupo: Optional[str] = None
    jornada: Optional[str] = None
    estado: Optional[str] = None
    sede: Optional[str] = None
    identificador: Optional[str] = None
    flg_virtual: Optional[str] = None
    nombre_facultad: Optional[str] = None
    semilla: Optional[str] = None

    class Config:
        from_attributes = True


class InscripcionCreate(BaseModel):
    estudiante_cedula: str
    periodo: str
    ciclo_ingreso: Optional[str] = None
    cod_plan: Optional[str] = None
    nom_plan: Optional[str] = None
    cod_asignatura: Optional[str] = None
    asignatura: Optional[str] = None
    ciclo: Optional[str] = None
    creditos: Optional[str] = None
    grupo: Optional[str] = None
    jornada: Optional[str] = None
    estado: Optional[str] = None
    sede: Optional[str] = None
    identificador: Optional[str] = None
    flg_virtual: Optional[str] = None
    nombre_facultad: Optional[str] = None
    semilla: Optional[str] = None


class InscripcionUpdate(BaseModel):
    estudiante_cedula: Optional[str] = None
    periodo: Optional[str] = None
    ciclo_ingreso: Optional[str] = None
    cod_plan: Optional[str] = None
    nom_plan: Optional[str] = None
    cod_asignatura: Optional[str] = None
    asignatura: Optional[str] = None
    ciclo: Optional[str] = None
    creditos: Optional[str] = None
    grupo: Optional[str] = None
    jornada: Optional[str] = None
    estado: Optional[str] = None
    sede: Optional[str] = None
    identificador: Optional[str] = None
    flg_virtual: Optional[str] = None
    nombre_facultad: Optional[str] = None
    semilla: Optional[str] = None


# ---------- Cargas ----------
class CargaArchivoOut(BaseModel):
    id: int
    tipo: str
    nombre_archivo: Optional[str]
    periodo: Optional[str]
    filas_procesadas: int
    filas_error: int
    duplicados_omitidos: Optional[int] = 0
    estado: str
    creado_en: Optional[datetime] = None

    class Config:
        from_attributes = True
