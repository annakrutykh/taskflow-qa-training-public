"""Журнал мутирующих действий (app.models.AuditLog).

record_audit() только добавляет объект в сессию — коммит делает вызывающий
код как часть той же транзакции, что и само действие.
"""

from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog, User


def record_audit(
    db: Session,
    user: User | None,
    action: str,
    entity_type: str,
    entity_id: int,
    details: dict[str, Any] | None = None,
) -> None:
    db.add(
        AuditLog(
            user_id=user.id if user else None,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
        )
    )
