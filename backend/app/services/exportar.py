"""
Generación de horario en formato .ics (calendario) y .pdf, tanto para
estudiantes como para docentes. Los horarios no traen fecha exacta de
inicio/fin de semestre, así que el evento .ics se genera como una cita
semanal recurrente (RRULE) que arranca en la próxima fecha en que caiga
ese día de la semana, y se repite por ~16 semanas (duración típica de un
ciclo académico); el usuario puede ajustar o borrar el evento libremente
en su calendario.
"""
import os
import uuid
from datetime import datetime, date, timedelta, time as dtime
from io import BytesIO
from typing import Iterable

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet

LOGO_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "logo-pinter.png")

DIAS_ISO = {
    "1. LUNES": 0,
    "2. MARTES": 1,
    "3. MIERCOLES": 2,
    "3. MIÉRCOLES": 2,
    "4. JUEVES": 3,
    "5. VIERNES": 4,
    "6. SABADO": 5,
    "6. SÁBADO": 5,
    "7. DOMINGO": 6,
}

SEMANAS_CICLO = 16


def _dia_a_iso(dia: str):
    if not dia:
        return None
    clave = dia.strip().upper()
    return DIAS_ISO.get(clave)


def _proxima_fecha_para(dia_iso: int, desde: date) -> date:
    delta = (dia_iso - desde.weekday()) % 7
    return desde + timedelta(days=delta)


def generar_ics(horarios: Iterable, titulo_calendario: str) -> str:
    hoy = date.today()
    lineas = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Consulta de Horarios PINTER//ES",
        "CALSCALE:GREGORIAN",
        f"X-WR-CALNAME:{titulo_calendario}",
    ]

    for h in horarios:
        dia_iso = _dia_a_iso(h.dia)
        if dia_iso is None or not h.hora_inicio or not h.hora_fin:
            continue

        fecha_inicio = _proxima_fecha_para(dia_iso, hoy)
        dtstart = datetime.combine(fecha_inicio, h.hora_inicio)
        dtend = datetime.combine(fecha_inicio, h.hora_fin)
        uid = f"{uuid.uuid4()}@consulta-horario-pinter"

        resumen = h.asignatura or "Clase"
        lugar = ", ".join(filter(None, [h.sede, h.nombre_salon]))
        descripcion = (
            f"Grupo: {h.grupo or ''}\\n"
            f"Docente: {h.nombre_docente or ''}\\n"
            f"Programa: {h.programa or ''}\\n"
            f"Periodo: {h.periodo or ''}"
        )

        lineas += [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}",
            f"DTSTART:{dtstart.strftime('%Y%m%dT%H%M%S')}",
            f"DTEND:{dtend.strftime('%Y%m%dT%H%M%S')}",
            f"RRULE:FREQ=WEEKLY;COUNT={SEMANAS_CICLO}",
            f"SUMMARY:{resumen}",
            f"LOCATION:{lugar}",
            f"DESCRIPTION:{descripcion}",
            "END:VEVENT",
        ]

    lineas.append("END:VCALENDAR")
    return "\r\n".join(lineas) + "\r\n"


def generar_pdf(horarios: list, titulo: str, subtitulo: str = "") -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(letter),
        topMargin=1.2 * cm, bottomMargin=1.2 * cm, leftMargin=1.2 * cm, rightMargin=1.2 * cm,
    )
    estilos = getSampleStyleSheet()
    elementos = []

    if os.path.isfile(LOGO_PATH):
        try:
            logo = Image(LOGO_PATH, width=4.2 * cm, height=1.85 * cm)
            logo.hAlign = "LEFT"
            elementos.append(logo)
            elementos.append(Spacer(1, 6))
        except Exception:
            pass  # si la imagen no se puede leer, el PDF se genera igual sin logo

    elementos.append(Paragraph(titulo, estilos["Title"]))
    if subtitulo:
        elementos.append(Paragraph(subtitulo, estilos["Normal"]))
    elementos.append(Spacer(1, 12))

    encabezado = ["Día", "Hora", "Sede", "Salón", "Materia", "Grupo", "Docente"]
    filas = [encabezado]
    for h in sorted(horarios, key=lambda x: (x.dia or "", str(x.hora_inicio or ""))):
        hora = f"{h.hora_inicio} - {h.hora_fin}" if h.hora_inicio and h.hora_fin else ""
        filas.append([
            (h.dia or "").replace("_", " "),
            hora,
            h.sede or "",
            h.nombre_salon or "",
            h.asignatura or "",
            h.grupo or "",
            h.nombre_docente or "",
        ])

    if len(filas) == 1:
        filas.append(["Sin registros de horario disponibles", "", "", "", "", "", ""])

    tabla = Table(filas, repeatRows=1)
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0b3d91")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#e8effc")]),
    ]))
    elementos.append(tabla)
    doc.build(elementos)
    return buffer.getvalue()
