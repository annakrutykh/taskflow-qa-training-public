"""Вспомогательные функции для soft delete (ADR-08).

Session.get() ищет строго по первичному ключу и не умеет накладывать
дополнительные условия — soft-удалённая строка была бы найдена так же,
как активная. get_active() — обёртка с явным фильтром deleted_at IS NULL
для моделей, поддерживающих soft delete (User, Project, Task, Comment).
"""

from sqlalchemy.orm import Session


def get_active(db: Session, model, entity_id: int):
    return (
        db.query(model)
        .filter(model.id == entity_id, model.deleted_at.is_(None))
        .first()
    )
