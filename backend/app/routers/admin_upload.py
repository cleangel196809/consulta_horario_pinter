from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import require_admin
from ..services.excel_import import importar_planeacion, importar_inscritos

router = APIRouter(prefix="/api/admin", tags=["administracion"])

EXTENSIONES_VALIDAS = (".xlsx", ".xlsm")


def _validar_extension(filename: str):
    if not filename.lower().endswith(EXTENSIONES_VALIDAS):
        raise HTTPException(
            status_code=400,
            detail="Solo se aceptan archivos Excel (.xlsx / .xlsm).",
        )


@router.post("/cargar-planeacion", response_model=schemas.CargaArchivoOut)
def cargar_planeacion(
    periodo: str = Form(..., description="Ciclo/periodo, ej: 2026-3T"),
    archivo: UploadFile = File(...),
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
        resultado = importar_planeacion(db, contenido, periodo, carga.id)
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
