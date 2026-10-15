"""Auditoría compartida.

`patients._audit` era el único punto que registraba cambios, pero el docstring
de `AuditLog` promete también los de turnos/agenda. Un módulo aparte evita el
circuito de imports entre blueprints (agenda → patients → agenda).

La función **no commitea**: el que llama hace el `db.session.commit()` junto
con su propio cambio, así si algo falla no queda el log huérfano.
"""
import json

from flask_login import current_user

from extensions import db
from models import AuditLog


def audit(entity_type, entity_id, action, changes=None):
    """Registra una acción de auditoría (sin commitear)."""
    db.session.add(AuditLog(
        user_id=current_user.id if current_user.is_authenticated else None,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        changes=json.dumps(changes, ensure_ascii=False,
                           default=str) if changes else None,
    ))
