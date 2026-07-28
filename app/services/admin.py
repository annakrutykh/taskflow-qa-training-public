"""Административные операции обслуживания БД (CLAUDE.md, раздел 5)."""

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.audit import record_audit
from app.core.db_utils import get_active
from app.core.seed import seed_database
from app.models import User

_TABLES = (
    "audit_log",
    "task_labels",
    "comments",
    "tasks",
    "project_members",
    "projects",
    "labels",
    "users",
)


def reset_database(db: Session, actor: User) -> None:
    """Полностью очищает все данные и заново заполняет их из seed.py.

    Необратимо.
    """
    actor_id = actor.id

    db.execute(text(f"TRUNCATE TABLE {', '.join(_TABLES)} RESTART IDENTITY CASCADE"))
    db.commit()
    db.expunge_all()

    seed_database(db)

    # actor мог ссылаться на строку, которую TRUNCATE уже убрал из identity
    # map сессии — перечитываем по сохранённому id, чтобы не словить
    # SAWarning о повторно занятом identity-ключе при флаше seed-данных.
    record_audit(db, get_active(db, User, actor_id), "admin.reset", "database", 0)

    db.commit()
