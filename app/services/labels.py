"""Бизнес-логика меток и их привязки к задачам (CLAUDE.md, раздел 5)."""

from sqlalchemy.orm import Session

from app.core.audit import record_audit
from app.core.errors import LabelAlreadyExistsError, NotFoundError
from app.models import Label, User
from app.permissions import get_accessible_task, require_task_manage


def create_label(db: Session, user: User, name: str) -> Label:
    """Создаёт метку.

    Бросает: LabelAlreadyExistsError, если метка с таким именем уже есть.
    """
    if db.query(Label).filter_by(name=name).first():
        raise LabelAlreadyExistsError("Метка с таким названием уже существует")

    label = Label(name=name)

    db.add(label)
    db.flush()

    record_audit(db, user, "label.create", "label", label.id)

    db.commit()
    db.refresh(label)

    return label


def list_labels(db: Session, limit: int, offset: int) -> tuple[list[Label], int]:
    """Возвращает страницу меток, отсортированных по id."""
    query = db.query(Label).order_by(Label.id.asc())
    total = query.count()
    items = query.offset(offset).limit(limit).all()

    return items, total


def attach_label(db: Session, user: User, task_id: int, label_id: int) -> None:
    """Привязывает метку к задаче (идемпотентно).

    Бросает: NotFoundError (задача/метка), ForbiddenError.
    """
    task = get_accessible_task(db, task_id, user)
    require_task_manage(db, task, user)

    label = db.get(Label, label_id)

    if not label:
        raise NotFoundError("Метка не найдена")

    if label not in task.labels:
        task.labels.append(label)
        record_audit(
            db,
            user,
            "task.label_attach",
            "task",
            task.id,
            {"labelId": label_id},
        )
        db.commit()


def detach_label(db: Session, user: User, task_id: int, label_id: int) -> None:
    """Отвязывает метку от задачи (идемпотентно — не бросает, если метки не было).

    Бросает: NotFoundError (задача), ForbiddenError.
    """
    task = get_accessible_task(db, task_id, user)
    require_task_manage(db, task, user)

    label = db.get(Label, label_id)

    if label is not None and label in task.labels:
        task.labels.remove(label)
        record_audit(
            db,
            user,
            "task.label_detach",
            "task",
            task.id,
            {"labelId": label_id},
        )
        db.commit()


def delete_label(db: Session, user: User, label_id: int) -> None:
    """Удаляет метку целиком (каскад на привязки — на уровне БД).

    Бросает: NotFoundError, если метка не найдена.
    """
    label = db.get(Label, label_id)

    if not label:
        raise NotFoundError("Метка не найдена")

    db.delete(label)

    record_audit(db, user, "label.delete", "label", label_id)

    db.commit()
