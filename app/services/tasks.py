"""Бизнес-логика задач (CLAUDE.md, раздел 5)."""

from datetime import UTC, datetime

from sqlalchemy import case, or_
from sqlalchemy.orm import Session

from app.core.audit import record_audit
from app.core.db_utils import get_active
from app.core.defects import defects
from app.core.errors import ForbiddenError, NotFoundError, UnknownSortFieldError
from app.models import Comment, Project, ProjectMember, ProjectRole, Task, User
from app.permissions import (
    TaskAccess,
    get_accessible_task,
    get_task_access,
    require_project_role,
    require_task_manage,
)

_PRIORITY_SORT_COLUMN = (
    Task.priority
    if defects.is_enabled("D-01")
    else case(
        (Task.priority == "LOW", 0),
        (Task.priority == "MEDIUM", 1),
        (Task.priority == "HIGH", 2),
    )
)

TASK_RESPONSE_EXCLUDE = {"labels"} if defects.is_enabled("D-04") else None
TASK_LIST_RESPONSE_EXCLUDE = (
    {"items": {"__all__": {"labels"}}} if defects.is_enabled("D-04") else None
)


def create_task(
    db: Session,
    user: User,
    project_id: int,
    title: str,
    description: str | None,
    priority: str,
    assignee_id: int | None,
) -> Task:
    """Создаёт задачу в проекте.

    Бросает: NotFoundError (проект/исполнитель), ForbiddenError.
    """
    project = get_active(db, Project, project_id)

    if not project:
        raise NotFoundError("Проект не найден")

    require_project_role(db, project, user, ProjectRole.MANAGER)

    if assignee_id is not None and not get_active(db, User, assignee_id):
        raise NotFoundError("Исполнитель не найден")

    task = Task(
        project_id=project_id,
        title=title,
        description=description,
        priority=priority,
        assignee_id=assignee_id,
    )

    db.add(task)
    db.flush()

    record_audit(db, user, "task.create", "task", task.id)

    db.commit()
    db.refresh(task)

    return task


def list_tasks(
    db: Session,
    user: User,
    limit: int,
    offset: int,
    status: str | None,
    priority: str | None,
    assignee_id: int | None,
    project_id: int | None,
    search: str | None,
    sort: str | None,
    order: str,
) -> tuple[list[Task], int]:
    """Возвращает задачи из проектов пользователя-участника плюс назначенные
    напрямую (ADMIN — все задачи), с фильтрацией/поиском/сортировкой.

    Бросает: UnknownSortFieldError, если `sort` не входит в допустимый набор.
    """
    query = db.query(Task).filter(Task.deleted_at.is_(None))

    if user.role != "ADMIN":
        member_project_ids = db.query(ProjectMember.project_id).filter(
            ProjectMember.user_id == user.id
        )
        query = query.filter(
            or_(
                Task.project_id.in_(member_project_ids),
                Task.assignee_id == user.id,
            )
        )

    if status:
        query = query.filter(Task.status == status)

    if priority:
        query = query.filter(Task.priority == priority)

    if assignee_id is not None:
        query = query.filter(Task.assignee_id == assignee_id)

    if project_id is not None:
        query = query.filter(Task.project_id == project_id)

    if search:
        query = query.filter(Task.title.ilike(f"%{search}%"))

    sort_fields = {
        "createdAt": Task.created_at,
        "priority": _PRIORITY_SORT_COLUMN,
        "title": Task.title,
        "status": Task.status,
    }

    if sort:
        if sort not in sort_fields:
            raise UnknownSortFieldError("Неизвестное поле сортировки")

        column = sort_fields[sort]

        if order == "desc":
            query = query.order_by(column.desc(), Task.id.asc())
        else:
            query = query.order_by(column.asc(), Task.id.asc())
    else:
        query = query.order_by(Task.id.asc())

    total = query.count()
    items = query.offset(offset).limit(limit).all()

    return items, total


def get_task(db: Session, user: User, task_id: int) -> Task:
    """Возвращает задачу, если у пользователя есть к ней доступ."""
    return get_accessible_task(db, task_id, user)


def update_task(db: Session, user: User, task_id: int, provided_fields: dict) -> Task:
    """Обновляет переданное подмножество полей задачи в рамках уровня доступа
    вызывающего (MANAGER+ — любые поля, включая переназначение исполнителя;
    ASSIGNEE — только status).

    Бросает: NotFoundError (задача, либо новый исполнитель не найден),
    ForbiddenError (в т.ч. при попытке изменить поле вне разрешённого набора).
    """
    task = get_accessible_task(db, task_id, user)
    access = get_task_access(db, task, user)

    if access == TaskAccess.MANAGER:
        allowed_fields = {
            "title",
            "description",
            "status",
            "priority",
            "assignee_id",
        }
    elif access == TaskAccess.ASSIGNEE:
        allowed_fields = {"status"}
    else:
        allowed_fields = set()

    disallowed = provided_fields.keys() - allowed_fields

    if disallowed:
        raise ForbiddenError(
            f"Недостаточно прав для изменения полей: {', '.join(sorted(disallowed))}"
        )

    new_assignee_id = provided_fields.get("assignee_id")
    if new_assignee_id is not None and not get_active(db, User, new_assignee_id):
        raise NotFoundError("Исполнитель не найден")

    for field, value in provided_fields.items():
        setattr(task, field, value)

    if provided_fields:
        record_audit(db, user, "task.update", "task", task.id, provided_fields)

    db.commit()
    db.refresh(task)

    return task


def delete_task(db: Session, user: User, task_id: int) -> None:
    """Удаляет задачу (soft delete), каскадно помечая её комментарии.

    Бросает: NotFoundError, ForbiddenError.
    """
    task = get_accessible_task(db, task_id, user)
    require_task_manage(db, task, user)

    now = datetime.now(UTC)

    db.query(Comment).filter(
        Comment.task_id == task_id, Comment.deleted_at.is_(None)
    ).update({"deleted_at": now}, synchronize_session=False)

    task.deleted_at = now

    record_audit(db, user, "task.delete", "task", task.id)

    db.commit()
