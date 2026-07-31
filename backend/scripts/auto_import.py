#!/usr/bin/env python3
"""
Carga automatica (programada) de los archivos de PLANEACION e INSCRITOS
desde una carpeta compartida, para no depender de que el administrador
entre manualmente a subirlos cada ciclo.

Uso tipico: programar este script con cron (Linux/Mac) o con el
Programador de tareas de Windows para que se ejecute, por ejemplo, cada
noche. El script:

  1. Revisa una carpeta (WATCH_DIR) buscando archivos .xlsx cuyo nombre
     contenga "PLANEACION" o "INSCRITOS".
  2. Se fija en la fecha de modificacion del archivo: si ya fue
     procesado antes (mismo nombre + misma fecha de modificacion, segun
     el registro en la tabla cargas_archivo), lo omite.
  3. Si es nuevo, lo importa usando la misma logica que el panel de
     administrador (backend/app/services/excel_import.py) y deja el
     registro correspondiente en cargas_archivo con el nombre de usuario
     "auto_import" (se crea automaticamente si no existe).

Variables de entorno esperadas (ademas de las de conexion a Postgres,
que ya usa la app -- POSTGRES_HOST, POSTGRES_USER, etc.):

  WATCH_DIR   Carpeta a inspeccionar. Por defecto: /data/carga_automatica
  PERIODO     Periodo/ciclo a asignar a los archivos importados (ej. 2026-3T).
              Si no se define, se intenta extraer del nombre del archivo.

Ejemplo de linea de cron (todos los dias a la 1:00 a.m.):
  0 1 * * *  docker exec pinter_api python scripts/auto_import.py >> /var/log/pinter_auto_import.log 2>&1

En Windows, se puede usar el Programador de tareas para ejecutar:
  docker exec pinter_api python scripts/auto_import.py
"""
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal  # noqa: E402
from app import models  # noqa: E402
from app.services.excel_import import importar_planeacion, importar_inscritos  # noqa: E402

WATCH_DIR = Path(os.environ.get("WATCH_DIR", "/data/carga_automatica"))
PERIODO_FORZADO = os.environ.get("PERIODO")
USUARIO_AUTOMATICO = "auto_import"


def _detectar_periodo(nombre_archivo: str) -> str:
    if PERIODO_FORZADO:
        return PERIODO_FORZADO
    m = re.search(r"(20\d{2}-\d?[A-Za-z]?\d?T?)", nombre_archivo)
    if m:
        return m.group(1)
    return datetime.now().strftime("%Y-%mT")


def _obtener_usuario_automatico(db):
    usuario = db.query(models.Usuario).filter(models.Usuario.username == USUARIO_AUTOMATICO).first()
    if not usuario:
        from app.security import hash_password
        usuario = models.Usuario(
            username=USUARIO_AUTOMATICO,
            password_hash=hash_password(os.urandom(16).hex()),
            nombre_completo="Carga automática (cron)",
            rol="admin",
            activo=False,  # no debe poder iniciar sesión, solo se usa como referencia
        )
        db.add(usuario)
        db.commit()
        db.refresh(usuario)
    return usuario


def _ya_procesado(db, nombre_archivo: str, mtime_iso: str) -> bool:
    existente = (
        db.query(models.CargaArchivo)
        .filter(models.CargaArchivo.nombre_archivo == f"{nombre_archivo}|{mtime_iso}")
        .first()
    )
    return existente is not None


def procesar_carpeta():
    if not WATCH_DIR.is_dir():
        print(f"[auto_import] La carpeta '{WATCH_DIR}' no existe. Nada que hacer.")
        return

    db = SessionLocal()
    usuario = _obtener_usuario_automatico(db)
    procesados = 0

    try:
        for archivo in sorted(WATCH_DIR.glob("*.xlsx")):
            mtime_iso = datetime.fromtimestamp(archivo.stat().st_mtime, tz=timezone.utc).isoformat()
            marca = f"{archivo.name}|{mtime_iso}"

            if _ya_procesado(db, archivo.name, mtime_iso):
                continue

            nombre_upper = archivo.name.upper()
            if "PLANEACION" in nombre_upper or "PLANEACIÓN" in nombre_upper:
                tipo = "planeacion"
            elif "INSCRITO" in nombre_upper:
                tipo = "inscritos"
            else:
                print(f"[auto_import] Se omite '{archivo.name}': no se reconoce si es planeación o inscritos.")
                continue

            periodo = _detectar_periodo(archivo.name)
            contenido = archivo.read_bytes()

            carga = models.CargaArchivo(
                tipo=tipo, nombre_archivo=marca, periodo=periodo,
                usuario_id=usuario.id, estado="procesando",
            )
            db.add(carga)
            db.commit()
            db.refresh(carga)

            try:
                if tipo == "planeacion":
                    resultado = importar_planeacion(db, contenido, periodo, carga.id)
                else:
                    resultado = importar_inscritos(db, contenido, periodo, carga.id)
                carga.filas_procesadas = resultado["filas_procesadas"]
                carga.filas_error = resultado["filas_error"]
                carga.estado = "completado"
                print(f"[auto_import] '{archivo.name}' ({tipo}, periodo {periodo}): {resultado}")
                procesados += 1
            except Exception as exc:
                carga.estado = "error"
                carga.detalle_error = str(exc)[:2000]
                print(f"[auto_import] ERROR procesando '{archivo.name}': {exc}")

            db.commit()
    finally:
        db.close()

    print(f"[auto_import] Terminado. Archivos nuevos procesados: {procesados}")


if __name__ == "__main__":
    procesar_carpeta()
