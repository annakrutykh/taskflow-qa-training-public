"""Бизнес-логика комментариев к задачам (CLAUDE.md, раздел 5)."""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.audit import record_audit
from app.core.errors import ForbiddenError, NotFoundError
from app.models import Comment, User
from app.permissions import TaskAccess, get_accessible_task, get_task_access


def _get_active_comment(db: Session, task_id: int, comment_id: int) -> Comment | None:
    return (
        db.query(Comment)
        .filter(
            Comment.id == comment_id,
            Comment.task_id == task_id,
            Comment.deleted_at.is_(None),
        )
        .first()
    )


def create_comment(db: Session, user: User, task_id: int, text: str) -> Comment:
    """Добавляет комментарий к задаче, если у пользователя есть к ней доступ."""
    get_accessible_task(db, task_id, user)

    comment = Comment(task_id=task_id, author_id=user.id, text=text)

    db.add(comment)
    db.flush()

    record_audit(db, user, "comment.create", "comment", comment.id)

    db.commit()
    db.refresh(comment)

    return comment


def list_comments(
    db: Session, user: User, task_id: int, limit: int, offset: int
) -> tuple[list[Comment], int]:
    """Возвращает комментарии задачи, если у пользователя есть к ней доступ."""
    get_accessible_task(db, task_id, user)

    query = (
        db.query(Comment)
        .filter(Comment.task_id == task_id, Comment.deleted_at.is_(None))
        .order_by(Comment.id.asc())
    )
    total = query.count()
    items = query.offset(offset).limit(limit).all()

    return items, total


def update_comment(
    db: Session, user: User, task_id: int, comment_id: int, text: str
) -> Comment:
    """Обновляет текст комментария. Доступ — только автор.

    Бросает: NotFoundError, ForbiddenError.
    """
    get_accessible_task(db, task_id, user)

    comment = _get_active_comment(db, task_id, comment_id)

    if not comment:
        raise NotFoundError("Комментарий не найден")

    if comment.author_id != user.id:
        raise ForbiddenError("Редактировать комментарий может только его автор")

    comment.text = text

    record_audit(db, user, "comment.update", "comment", comment.id)

    db.commit()
    db.refresh(comment)

    return comment


def delete_comment(db: Session, user: User, task_id: int, comment_id: int) -> None:
    """Удаляет комментарий (soft delete). Доступ — автор либо MANAGER+/ADMIN
    участник проекта задачи.

    Бросает: NotFoundError, ForbiddenError.
    """
    task = get_accessible_task(db, task_id, user)

    comment = _get_active_comment(db, task_id, comment_id)

    if not comment:
        raise NotFoundError("Комментарий не найден")

    if (
        comment.author_id != user.id
        and get_task_access(db, task, user) != TaskAccess.MANAGER
    ):
        raise ForbiddenError("Недостаточно прав")

    comment.deleted_at = datetime.now(UTC)

    record_audit(db, user, "comment.delete", "comment", comment.id)

    db.commit()
