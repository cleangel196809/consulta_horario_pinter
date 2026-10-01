import json

from sqlalchemy.orm import Session

from .. import models


def registrar(db: Session, accion: str, recurso: str, usuario=None, recurso_id=None, detalle=None):
    db.add(models.Auditoria(
        usuario_id=getattr(usuario, "id", None),
        username=getattr(usuario, "username", None),
        accion=accion,
        recurso=recurso,
        recurso_id=str(recurso_id) if recurso_id is not None else None,
        detalle=json.dumps(detalle, ensure_ascii=False) if detalle else None,
    ))
