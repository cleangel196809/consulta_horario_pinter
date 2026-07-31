"""
Envío de notificaciones por correo cuando se carga o modifica un horario.
Requiere configurar las variables SMTP_* en el .env; si no están
configuradas, las funciones devuelven un resultado indicando que el envío
está deshabilitado en vez de fallar o intentar conectarse a un servidor
inexistente.
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Iterable

from ..config import settings


def _enviar_correo(destinatario: str, asunto: str, cuerpo_html: str) -> bool:
    if not settings.smtp_configurado:
        return False
    msg = MIMEMultipart("alternative")
    msg["Subject"] = asunto
    msg["From"] = settings.smtp_from
    msg["To"] = destinatario
    msg.attach(MIMEText(cuerpo_html, "html", "utf-8"))

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
        if settings.smtp_use_tls:
            server.starttls()
        server.login(settings.smtp_user, settings.smtp_password)
        server.sendmail(settings.smtp_from, [destinatario], msg.as_string())
    return True


def notificar_carga(
    periodo: str, tipo: str, destinatarios: Iterable[tuple[str, str]]
) -> dict:
    """destinatarios: iterable de (nombre, correo). Devuelve un resumen de
    cuántos correos se enviaron y cuántos fallaron."""
    if not settings.smtp_configurado:
        return {
            "habilitado": False,
            "mensaje": "El envío de correo no está configurado (faltan variables SMTP_* en el .env).",
            "enviados": 0,
            "fallidos": 0,
        }

    enviados, fallidos = 0, 0
    detalle_errores = []
    asunto = f"Actualización de horario - {tipo} - {periodo}"
    for nombre, correo in destinatarios:
        if not correo:
            continue
        cuerpo = f"""
        <p>Hola {nombre or ''},</p>
        <p>Se actualizó la información de horarios para el período <b>{periodo}</b>
        en el sistema de Consulta de Horarios PINTER.</p>
        <p>Ingresa a la aplicación para revisar tu horario actualizado.</p>
        <p>Este es un mensaje automático, por favor no respondas a este correo.</p>
        """
        try:
            if _enviar_correo(correo, asunto, cuerpo):
                enviados += 1
        except Exception as exc:
            fallidos += 1
            detalle_errores.append(f"{correo}: {exc}")

    return {
        "habilitado": True,
        "enviados": enviados,
        "fallidos": fallidos,
        "errores": detalle_errores[:20],
    }
