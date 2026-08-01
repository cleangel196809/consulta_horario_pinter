from typing import List, Optional

import openpyxl
from io import BytesIO

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import require_admin
from ..services.excel_import import importar_planeacion, importar_inscritos, detectar_duplicados_planeacion
from ..services.notificaciones import notificar_carga

router = APIRouter(prefix="/api/admin", tags=["administracion"])

EXTENSIONES_VALIDAS = (".xlsx", ".xlsm")


def _validar_extension(filename: str):
    if not filename.lower().endswith(EXTENSIONES_VALIDAS):
        raise HTTPException(
            status_code=400,
            detail="Solo se aceptan archivos Excel (.xlsx / .xlsm).",
        )


@router.post("/cargar-planeacion/previsualizar")
def previsualizar_planeacion(
    periodo: str = Form(..., description="Ciclo/periodo, ej: 2026-3T"),
    archivo: UploadFile = File(...),
    current_user: models.Usuario = Depends(require_admin),
):
    """Analiza el archivo de PLANEACIÓN SIN insertar nada en la base de
    datos y devuelve un resumen de posibles filas duplicadas (dos filas se
    consideran la misma clase si coinciden EXACTAMENTE en docente + día +
    hora_inicio + hora_fin + salón + grupo + asignatura, dentro del periodo
    a cargar).

    Flujo de uso pensado para el frontend:
      1) El admin sube el archivo -> el frontend llama a este endpoint.
      2) Si `duplicados_encontrados > 0`, el frontend le muestra la lista de
         `grupos_duplicados` y pregunta "¿deseas eliminar los duplicados?".
      3) El admin confirma (o no) y el frontend vuelve a llamar al endpoint
         real `POST /api/admin/cargar-planeacion`, esta vez con el mismo
         archivo + periodo y `eliminar_duplicados=true` (o `false` si el
         admin prefiere cargar todo tal cual).

    Este endpoint nunca modifica la base de datos ni borra nada por su
    cuenta: solo informa.
    """
    _validar_extension(archivo.filename)
    contenido = archivo.file.read()
    try:
        wb = openpyxl.load_workbook(BytesIO(contenido), data_only=True)
        resultado = detectar_duplicados_planeacion(wb, periodo)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"No se pudo analizar el archivo: {exc}")
    return resultado


@router.post("/cargar-planeacion", response_model=schemas.CargaArchivoOut)
def cargar_planeacion(
    periodo: str = Form(..., description="Ciclo/periodo, ej: 2026-3T"),
    archivo: UploadFile = File(...),
    eliminar_duplicados: bool = Form(
        False,
        description=(
            "Si es true, se conserva solo la primera fila de cada grupo de "
            "filas duplicadas (ver /cargar-planeacion/previsualizar) y se "
            "descartan las demás antes de insertar. Por defecto es false: "
            "el admin SIEMPRE debe decidir explícitamente eliminar "
            "duplicados, nunca se borran automáticamente."
        ),
    ),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_admin),
):
    _validar_extension(archivo.filename)
    contenido = archivo.file.read()

    carga = models.CargaArchivo(
        tipo="planeacion",
        nombre_archivo=archivo.filename,
        periodo=periodo,
        usuario_id=current_user.id,
        estado="procesando",
    )
    db.add(carga)
    db.commit()
    db.refresh(carga)

    try:
        resultado = importar_planeacion(db, contenido, periodo, carga.id, eliminar_duplicados=eliminar_duplicados)
        carga.filas_procesadas = resultado["filas_procesadas"]
        carga.filas_error = resultado["filas_error"]
        carga.estado = "completado"
    except Exception as exc:
        carga.estado = "error"
        carga.detalle_error = str(exc)[:2000]
        db.commit()
        raise HTTPException(status_code=500, detail=f"Error al procesar el archivo: {exc}")

    db.commit()
    db.refresh(carga)
    return carga


@router.post("/cargar-inscritos", response_model=schemas.CargaArchivoOut)
def cargar_inscritos(
    periodo: str = Form(..., description="Ciclo/periodo, ej: 2026-3T"),
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_admin),
):
    _validar_extension(archivo.filename)
    contenido = archivo.file.read()

    carga = models.CargaArchivo(
        tipo="inscritos",
        nombre_archivo=archivo.filename,
        periodo=periodo,
        usuario_id=current_user.id,
        estado="procesando",
    )
    db.add(carga)
    db.commit()
    db.refresh(carga)

    try:
        resultado = importar_inscritos(db, contenido, periodo, carga.id)
        carga.filas_procesadas = resultado["filas_procesadas"]
        carga.filas_error = resultado["filas_error"]
        carga.estado = "completado"
    except Exception as exc:
        carga.estado = "error"
        carga.detalle_error = str(exc)[:2000]
        db.commit()
        raise HTTPException(status_code=500, detail=f"Error al procesar el archivo: {exc}")

    db.commit()
    db.refresh(carga)
    return carga


@router.get("/cargas", response_model=List[schemas.CargaArchivoOut])
def historial_de_cargas(
    tipo: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_admin),
):
    q = db.query(models.CargaArchivo)
    if tipo:
        q = q.filter(models.CargaArchivo.tipo == tipo)
    return q.order_by(models.CargaArchivo.creado_en.desc()).limit(100).all()


@router.post("/cargas/{carga_id}/notificar")
def notificar_afectados_de_carga(
    carga_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_admin),
):
    """Envía un correo a los docentes o estudiantes cuyo horario cambió en
    esta carga. Requiere que el administrador haya configurado SMTP_* en el
    .env; si no, informa claramente que el envío está deshabilitado."""
    carga = db.query(models.CargaArchivo).filter(models.CargaArchivo.id == carga_id).first()
    if not carga:
        raise HTTPException(status_code=404, detail="Carga no encontrada")

    if carga.tipo == "planeacion":
        filas = (
            db.query(models.Horario.nombre_docente, models.Horario.correo_docente)
            .filter(models.Horario.carga_id == carga_id)
            .distinct()
            .all()
        )
    else:
        filas = (
            db.query(
                (models.Estudiante.nombres + " " + models.Estudiante.apellidos),
                models.Estudiante.email,
            )
            .join(models.Inscripcion, models.Inscripcion.estudiante_cedula == models.Estudiante.cedula)
            .filter(models.Inscripcion.carga_id == carga_id)
            .distinct()
            .all()
        )

    resultado = notificar_carga(carga.periodo, carga.tipo, filas)
    return resultado
