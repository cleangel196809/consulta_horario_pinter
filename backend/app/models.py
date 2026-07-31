from sqlalchemy import (
    Column, BigInteger, String, Boolean, DateTime, Integer, Time, Text, ForeignKey, UniqueConstraint
)
from sqlalchemy.sql import func

from .database import Base


class Docente(Base):
    __tablename__ = "docentes"

    cedula = Column(BigInteger, primary_key=True)
    nombre_completo = Column(String(200), nullable=False)
    correo_institucional = Column(String(150))
    facultad = Column(String(150))
    sede = Column(String(100))
    activo = Column(Boolean, default=True)
    creado_en = Column(DateTime, server_default=func.now())
    actualizado_en = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Estudiante(Base):
    __tablename__ = "estudiantes"

    cedula = Column(String(30), primary_key=True)
    tipo = Column(String(30))
    nombres = Column(String(150))
    apellidos = Column(String(150))
    correo_aula_virtual = Column(String(150))
    email = Column(String(150))
    celular = Column(String(30))
    telefono = Column(String(30))
    ciclo_ingreso = Column(String(20))
    creado_en = Column(DateTime, server_default=func.now())
    actualizado_en = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Horario(Base):
    __tablename__ = "horarios"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    llave = Column(String(60))
    periodo = Column(String(20), nullable=False)
    codigo_asignatura = Column(String(20))
    facultad = Column(String(150))
    programa = Column(String(250))
    plan = Column(String(30))
    asignatura = Column(String(250))
    ciclo = Column(String(10))
    creditos = Column(String(10))
    grupo = Column(String(60), nullable=False)
    codigo_moodle = Column(String(100))
    codigo_teams = Column(String(100))
    enlace_teams = Column(Text)
    estado = Column(String(60))
    modalidad = Column(String(100))
    jornada = Column(String(60))
    capacidad = Column(Integer)
    dia = Column(String(30))
    hora_inicio = Column(Time)
    hora_fin = Column(Time)
    nombre_salon = Column(String(250))
    sede = Column(String(100))
    docente_cedula = Column(BigInteger, ForeignKey("docentes.cedula", ondelete="SET NULL"))
    nombre_docente = Column(String(200))
    correo_docente = Column(String(150))
    observaciones = Column(Text)
    origen_hoja = Column(String(30), default="PLANEACION")
    carga_id = Column(BigInteger)
    creado_en = Column(DateTime, server_default=func.now())
    actualizado_en = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Inscripcion(Base):
    __tablename__ = "inscripciones"
    __table_args__ = (
        UniqueConstraint("estudiante_cedula", "periodo", "cod_asignatura", "grupo", name="uq_inscripcion"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    estudiante_cedula = Column(String(30), ForeignKey("estudiantes.cedula", ondelete="CASCADE"), nullable=False)
    periodo = Column(String(20), nullable=False)
    ciclo_ingreso = Column(String(20))
    cod_plan = Column(String(30))
    nom_plan = Column(String(250))
    cod_asignatura = Column(String(20))
    asignatura = Column(String(250))
    ciclo = Column(String(10))
    creditos = Column(String(10))
    grupo = Column(String(60))
    jornada = Column(String(60))
    estado = Column(String(60))
    sede = Column(String(100))
    identificador = Column(String(120))
    flg_virtual = Column(String(5))
    nombre_facultad = Column(String(150))
    semilla = Column(String(60))
    carga_id = Column(BigInteger)
    creado_en = Column(DateTime, server_default=func.now())


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    username = Column(String(80), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    nombre_completo = Column(String(200))
    rol = Column(String(20), nullable=False, default="consulta")
    cedula_relacionada = Column(String(30))
    activo = Column(Boolean, default=True)
    creado_en = Column(DateTime, server_default=func.now())


class CargaArchivo(Base):
    __tablename__ = "cargas_archivo"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tipo = Column(String(30), nullable=False)
    nombre_archivo = Column(String(255))
    periodo = Column(String(20))
    usuario_id = Column(BigInteger, ForeignKey("usuarios.id"))
    filas_procesadas = Column(Integer, default=0)
    filas_error = Column(Integer, default=0)
    estado = Column(String(30), default="completado")
    detalle_error = Column(Text)
    creado_en = Column(DateTime, server_default=func.now())
