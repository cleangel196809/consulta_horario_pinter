"""
Sincronización automática de usuarios de login para docentes y estudiantes.

Decisión de diseño (no había una única forma "correcta" especificada, se
documenta aquí): en vez de crear una tabla nueva o un campo `tipo_perfil`
separado, se reutiliza la columna `usuarios.rol` agregando dos valores
nuevos:
  - "docente":             login de un docente.
  - "consulta_estudiante": login de un estudiante.

Ambos roles se comportan, a efectos de permisos, exactamente igual que el
rol "consulta" ya existente: son de solo lectura y no están sujetos al
filtro de alcance de `aplicar_alcance_coordinador` (que solo aplica al rol
"coordinador"). Ningún router de solo-lectura (horarios, docentes,
estudiantes, reportes) hace chequeos explícitos de rol distintos de
`require_admin`/`coordinador`, así que estos roles nuevos quedan
automáticamente habilitados para consultar sin cambios adicionales.

Reglas de negocio implementadas aquí:
- El `username` es el correo institucional (debe terminar en "@pi.edu.co").
  Para docentes se usa `correo_institucional`. Para estudiantes se prueba
  primero `email` y, si ese no termina en @pi.edu.co, se prueba
  `correo_aula_virtual`. Si ninguno de los dos termina en @pi.edu.co, el
  registro simplemente no puede loguearse (no se crea usuario y NO se
  considera un error de importación).
- La contraseña inicial es la cédula, tal cual, como texto.
- Se fuerza el cambio de contraseña en el primer ingreso
  (`debe_cambiar_password=True`).
- Si el usuario YA existe (por ejemplo, porque ya inició sesión antes y
  cambió su contraseña), esta sincronización NUNCA le pisa la contraseña
  ni vuelve a poner `debe_cambiar_password=True`: solo refresca datos
  informativos (nombre_completo, cedula_relacionada, activo=True).
"""
from typing import Optional

from sqlalchemy.orm import Session

from .. import models
from ..security import hash_password

ROL_DOCENTE = "docente"
ROL_CONSULTA_ESTUDIANTE = "consulta_estudiante"

DOMINIO_INSTITUCIONAL = "@pi.edu.co"


def _correo_institucional_valido(correo: Optional[str]) -> Optional[str]:
    """Devuelve el correo (limpio) si termina en @pi.edu.co, o None si no
    aplica (correo vacío, o de un dominio distinto)."""
    if not correo:
        return None
    correo = correo.strip()
    if not correo:
        return None
    if correo.lower().endswith(DOMINIO_INSTITUCIONAL):
        return correo
    return None


def _elegir_username(*candidatos: Optional[str]) -> Optional[str]:
    """Recorre los candidatos en orden de prioridad y devuelve el primero
    que sea un correo institucional válido."""
    for candidato in candidatos:
        correo = _correo_institucional_valido(candidato)
        if correo:
            return correo
    return None


def _sincronizar_usuario(
    db: Session,
    username: str,
    rol: str,
    cedula: str,
    nombre_completo: Optional[str],
) -> models.Usuario:
    usuario = db.query(models.Usuario).filter(models.Usuario.username == username).first()
    if usuario:
        # Ya existe: pudo haber cambiado su contraseña en algún momento, así
        # que NUNCA se toca password_hash ni debe_cambiar_password aquí.
        # Solo se refrescan datos informativos si cambiaron.
        cambiado = False
        if nombre_completo and usuario.nombre_completo != nombre_completo:
            usuario.nombre_completo = nombre_completo
            cambiado = True
        if not usuario.activo:
            usuario.activo = True
            cambiado = True
        if usuario.cedula_relacionada != str(cedula):
            usuario.cedula_relacionada = str(cedula)
            cambiado = True
        if cambiado:
            db.add(usuario)
        return usuario

    nuevo = models.Usuario(
        username=username,
        password_hash=hash_password(str(cedula)),
        nombre_completo=nombre_completo,
        rol=rol,
        cedula_relacionada=str(cedula),
        activo=True,
        debe_cambiar_password=True,
    )
    db.add(nuevo)
    return nuevo


def sincronizar_usuario_docente(
    db: Session,
    cedula,
    nombre_completo: Optional[str],
    correo_institucional: Optional[str],
) -> Optional[models.Usuario]:
    """Crea/actualiza el usuario de login de un docente. Devuelve None si el
    docente no tiene un correo @pi.edu.co válido (no se puede loguear)."""
    username = _elegir_username(correo_institucional)
    if not username or not cedula:
        return None
    return _sincronizar_usuario(db, username, ROL_DOCENTE, str(cedula), nombre_completo)


def sincronizar_usuario_estudiante(
    db: Session,
    cedula,
    nombre_completo: Optional[str],
    email: Optional[str],
    correo_aula_virtual: Optional[str],
) -> Optional[models.Usuario]:
    """Crea/actualiza el usuario de login de un estudiante. Se prueba primero
    `email` y luego `correo_aula_virtual`, usando el primero que termine en
    @pi.edu.co. Devuelve None si ninguno aplica."""
    username = _elegir_username(email, correo_aula_virtual)
    if not username or not cedula:
        return None
    return _sincronizar_usuario(db, username, ROL_CONSULTA_ESTUDIANTE, str(cedula), nombre_completo)
