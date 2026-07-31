from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from typing import Optional

from .. import models
from ..database import get_db
from ..deps import get_current_user
from ..services.exportar import generar_ics, generar_pdf

router = APIRouter(tags=["exportar"])


def _horario_estudiante(db: Session, cedula: str, periodo: Optional[str]):
    insc_q = db.query(models.Inscripcion).filter(models.Inscripcion.estudiante_cedula == cedula)
    if periodo:
        insc_q = insc_q.filter(models.Inscripcion.periodo == periodo)
    grupos = {i.grupo for i in insc_q.all() if i.grupo}
    if not grupos:
        return []
    q = db.query(models.Horario).filter(models.Horario.grupo.in_(grupos))
    if periodo:
        q = q.filter(models.Horario.periodo == periodo)
    return q.all()


@router.get("/api/estudiantes/{cedula}/horario.ics")
def horario_estudiante_ics(
    cedula: str, periodo: Optional[str] = None,
    db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user),
):
    estudiante = db.query(models.Estudiante).filter(models.Estudiante.cedula == cedula).first()
    if not estudiante:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    horarios = _horario_estudiante(db, cedula, periodo)
    nombre = f"{estudiante.nombres or ''} {estudiante.apellidos or ''}".strip() or cedula
    ics = generar_ics(horarios, f"Horario de {nombre}")
    return Response(
        content=ics, media_type="text/calendar",
        headers={"Content-Disposition": f'attachment; filename="horario_{cedula}.ics"'},
    )


@router.get("/api/estudiantes/{cedula}/horario.pdf")
def horario_estudiante_pdf(
    cedula: str, periodo: Optional[str] = None,
    db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user),
):
    estudiante = db.query(models.Estudiante).filter(models.Estudiante.cedula == cedula).first()
    if not estudiante:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    horarios = _horario_estudiante(db, cedula, periodo)
    nombre = f"{estudiante.nombres or ''} {estudiante.apellidos or ''}".strip() or cedula
    pdf = generar_pdf(horarios, f"Horario de {nombre}", f"Cédula: {cedula}" + (f" · Periodo: {periodo}" if periodo else ""))
    return Response(
        content=pdf, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="horario_{cedula}.pdf"'},
    )


@router.get("/api/docentes/{cedula}/horario.ics")
def horario_docente_ics(
    cedula: int, periodo: Optional[str] = None,
    db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user),
):
    docente = db.query(models.Docente).filter(models.Docente.cedula == cedula).first()
    if not docente:
        raise HTTPException(status_code=404, detail="Docente no encontrado")
    q = db.query(models.Horario).filter(models.Horario.docente_cedula == cedula)
    if periodo:
        q = q.filter(models.Horario.periodo == periodo)
    ics = generar_ics(q.all(), f"Horario de {docente.nombre_completo}")
    return Response(
        content=ics, media_type="text/calendar",
        headers={"Content-Disposition": f'attachment; filename="horario_docente_{cedula}.ics"'},
    )


@router.get("/api/docentes/{cedula}/horario.pdf")
def horario_docente_pdf(
    cedula: int, periodo: Optional[str] = None,
    db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user),
):
    docente = db.query(models.Docente).filter(models.Docente.cedula == cedula).first()
    if not docente:
        raise HTTPException(status_code=404, detail="Docente no encontrado")
    q = db.query(models.Horario).filter(models.Horario.docente_cedula == cedula)
    if periodo:
        q = q.filter(models.Horario.periodo == periodo)
    pdf = generar_pdf(
        q.all(), f"Horario de {docente.nombre_completo}",
        f"Cédula: {cedula}" + (f" · Periodo: {periodo}" if periodo else ""),
    )
    return Response(
        content=pdf, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="horario_docente_{cedula}.pdf"'},
    )
