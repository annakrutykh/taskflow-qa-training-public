"""Бизнес-логика проектов и их участников (CLAUDE.md, раздел 5)."""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.audit import record_audit
from app.core.cache import cache_delete, cache_get, cache_set
from app.core.db_utils import get_active
from app.core.errors import (
    LastProjectOwnerError,
    NotFoundError,
    ProjectMemberAlreadyExistsError,
    ValidationError,
)
from app.models import Comment, Project, ProjectMember, ProjectRole, Task, User
from app.permissions import get_membership, require_project_role

PROJECT_CACHE_TTL_SECONDS = 30


def _project_cache_key(project_id: int) -> str:
    return f"cache:project:{project_id}"


def create_project(
    db: Session, user: User, name: str, description: str | None
) -> Project:
    """Создаёт проект, создатель автоматически становится OWNER."""
    project = Project(name=name, description=description, owner_id=user.id)

    db.add(project)
    db.flush()

    db.add(
        ProjectMember(
            project_id=project.id,
            user_id=user.id,
            role=ProjectRole.OWNER,
        )
    )

    record_audit(db, user, "project.create", "project", project.id)

    db.commit()
    db.refresh(project)

    return project


def list_projects(
    db: Session, user: User, limit: int, offset: int
) -> tuple[list[Project], int]:
    """Возвращает проекты, где пользователь участник (ADMIN — все проекты)."""
    query = db.query(Project).filter(Project.deleted_at.is_(None))

    if user.role != "ADMIN":
        query = query.join(
            ProjectMember, ProjectMember.project_id == Project.id
        ).filter(ProjectMember.user_id == user.id)

    query = query.order_by(Project.id.asc())
    total = query.count()
    items = query.offset(offset).limit(limit).all()

    return items, total


def get_project(db: Session, user: User, project_id: int) -> Project:
    """Возвращает проект, если пользователь — участник любой роли или ADMIN.

    Содержимое проекта кэшируется в Redis на PROJECT_CACHE_TTL_SECONDS —
    оно одинаково для всех, кому вообще разрешено его увидеть, поэтому
    кэшируется отдельно от проверки прав: она выполняется на каждый вызов
    независимо от того, откуда взят объект проекта (см. app/core/cache.py).

    Бросает: NotFoundError, если проект не найден или доступа нет.
    """
    cache_key = _project_cache_key(project_id)
    cached = cache_get(cache_key)

    if cached is not None:
        project = Project(**cached)
    else:
        project = get_active(db, Project, project_id)

        if not project:
            raise NotFoundError("Проект не найден")

        cache_set(
            cache_key,
            {
                "id": project.id,
                "name": project.name,
                "description": project.description,
                "status": project.status,
                "owner_id": project.owner_id,
            },
            PROJECT_CACHE_TTL_SECONDS,
        )

    require_project_role(db, project, user, ProjectRole.VIEWER)

    return project


def update_project(
    db: Session, user: User, project_id: int, changed_fields: dict
) -> Project:
    """Обновляет переданное подмножество полей проекта.

    Бросает: NotFoundError, ForbiddenError (через require_project_role).
    """
    project = get_active(db, Project, project_id)

    if not project:
        raise NotFoundError("Проект не найден")

    require_project_role(db, project, user, ProjectRole.MANAGER)

    for field, value in changed_fields.items():
        setattr(project, field, value)

    if changed_fields:
        record_audit(db, user, "project.update", "project", project.id, changed_fields)

    db.commit()
    db.refresh(project)

    cache_delete(_project_cache_key(project.id))

    return project


def delete_project(db: Session, user: User, project_id: int) -> None:
    """Удаляет проект (soft delete), каскадно помечая его задачи и комментарии.

    Бросает: NotFoundError, ForbiddenError (через require_project_role).
    """
    project = get_active(db, Project, project_id)

    if not project:
        raise NotFoundError("Проект не найден")

    require_project_role(db, project, user, ProjectRole.OWNER)

    now = datetime.now(UTC)

    task_ids = [
        row.id
        for row in db.query(Task.id).filter(
            Task.project_id == project_id, Task.deleted_at.is_(None)
        )
    ]

    if task_ids:
        db.query(Comment).filter(
            Comment.task_id.in_(task_ids), Comment.deleted_at.is_(None)
        ).update({"deleted_at": now}, synchronize_session=False)

        db.query(Task).filter(Task.id.in_(task_ids)).update(
            {"deleted_at": now}, synchronize_session=False
        )

    project.deleted_at = now

    record_audit(
        db,
        user,
        "project.delete",
        "project",
        project.id,
        {"cascadedTasks": len(task_ids)},
    )

    db.commit()

    cache_delete(_project_cache_key(project.id))


def add_member(
    db: Session, user: User, project_id: int, target_user_id: int, role: str
) -> ProjectMember:
    """Добавляет пользователя в проект с указанной ролью.

    Глобальный ADMIN, добавленный в проект, всегда получает роль ADMIN
    (переданная роль игнорируется) — у него и так полный доступ, роль тут
    чисто информационная, любая другая была бы вводящей в заблуждение.
    Роль ADMIN, наоборот, нельзя присвоить обычному пользователю.

    Бросает: NotFoundError (проект/пользователь), ForbiddenError,
    ProjectMemberAlreadyExistsError, ValidationError (ADMIN — не тому).
    """
    project = get_active(db, Project, project_id)

    if not project:
        raise NotFoundError("Проект не найден")

    require_project_role(db, project, user, ProjectRole.OWNER)

    target_user = get_active(db, User, target_user_id)

    if not target_user:
        raise NotFoundError("Пользователь не найден")

    if target_user.role == "ADMIN":
        role = ProjectRole.ADMIN
    elif role == ProjectRole.ADMIN:
        raise ValidationError(
            "Роль ADMIN в проекте можно назначить только глобальному администратору"
        )

    if get_membership(db, project_id, target_user_id) is not None:
        raise ProjectMemberAlreadyExistsError("Пользователь уже участник проекта")

    membership = ProjectMember(
        project_id=project_id,
        user_id=target_user_id,
        role=role,
    )

    db.add(membership)

    record_audit(
        db,
        user,
        "project_member.add",
        "project",
        project_id,
        {"userId": target_user_id, "role": role},
    )

    db.commit()

    return membership


def list_members(
    db: Session, user: User, project_id: int, limit: int, offset: int
) -> tuple[list[ProjectMember], int]:
    """Возвращает участников проекта.

    Бросает: NotFoundError, ForbiddenError (через require_project_role).
    """
    project = get_active(db, Project, project_id)

    if not project:
        raise NotFoundError("Проект не найден")

    require_project_role(db, project, user, ProjectRole.VIEWER)

    query = (
        db.query(ProjectMember)
        .filter_by(project_id=project_id)
        .order_by(ProjectMember.user_id.asc())
    )
    total = query.count()
    items = query.offset(offset).limit(limit).all()

    return items, total


def update_member_role(
    db: Session, user: User, project_id: int, member_user_id: int, role: str
) -> ProjectMember:
    """Меняет роль участника проекта.

    Бросает: NotFoundError, ForbiddenError, LastProjectOwnerError (при
    попытке разжаловать последнего OWNER), ValidationError (роль ADMIN
    зарезервирована за глобальными ADMIN — см. add_member).
    """
    project = get_active(db, Project, project_id)

    if not project:
        raise NotFoundError("Проект не найден")

    require_project_role(db, project, user, ProjectRole.OWNER)

    membership = get_membership(db, project_id, member_user_id)

    if not membership:
        raise NotFoundError("Участник проекта не найден")

    if membership.user.role == "ADMIN":
        raise ValidationError(
            "Нельзя изменить роль в проекте у глобального администратора"
        )

    if role == ProjectRole.ADMIN:
        raise ValidationError(
            "Роль ADMIN в проекте можно назначить только глобальному администратору"
        )

    if membership.role == ProjectRole.OWNER and role != ProjectRole.OWNER:
        owner_count = (
            db.query(ProjectMember)
            .filter_by(project_id=project_id, role=ProjectRole.OWNER)
            .count()
        )

        if owner_count <= 1:
            raise LastProjectOwnerError(
                "Нельзя понизить в роли последнего владельца проекта"
            )

    membership.role = role

    record_audit(
        db,
        user,
        "project_member.role_update",
        "project",
        project_id,
        {"userId": member_user_id, "role": role},
    )

    db.commit()
    db.refresh(membership)

    return membership


def remove_member(
    db: Session, user: User, project_id: int, member_user_id: int
) -> None:
    """Удаляет участника проекта.

    Бросает: NotFoundError, ForbiddenError, LastProjectOwnerError (при
    попытке удалить последнего OWNER).
    """
    project = get_active(db, Project, project_id)

    if not project:
        raise NotFoundError("Проект не найден")

    require_project_role(db, project, user, ProjectRole.OWNER)

    membership = get_membership(db, project_id, member_user_id)

    if not membership:
        raise NotFoundError("Участник проекта не найден")

    if membership.role == ProjectRole.OWNER:
        owner_count = (
            db.query(ProjectMember)
            .filter_by(project_id=project_id, role=ProjectRole.OWNER)
            .count()
        )

        if owner_count <= 1:
            raise LastProjectOwnerError("Нельзя удалить последнего владельца проекта")

    db.delete(membership)

    record_audit(
        db,
        user,
        "project_member.remove",
        "project",
        project_id,
        {"userId": member_user_id},
    )

    db.commit()
