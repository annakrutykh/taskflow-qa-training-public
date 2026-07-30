"""Бизнес-логика управления пользователями (CLAUDE.md, раздел 5)."""

from datetime import UTC, datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.audit import record_audit
from app.core.db_utils import get_active
from app.core.errors import LastProjectOwnerError, NotFoundError
from app.models import ProjectMember, ProjectRole, User


def update_own_profile(
    db: Session,
    user: User,
    first_name: str | None,
    last_name: str | None,
) -> User:
    """Обновляет имя/фамилию текущего пользователя (только переданные поля)."""
    if first_name is not None:
        user.first_name = first_name

    if last_name is not None:
        user.last_name = last_name

    record_audit(db, user, "user.profile_update", "user", user.id)

    db.commit()
    db.refresh(user)

    return user


def list_users(db: Session, limit: int, offset: int) -> tuple[list[User], int]:
    """Возвращает страницу активных пользователей, отсортированных по id."""
    query = db.query(User).filter(User.deleted_at.is_(None)).order_by(User.id.asc())
    total = query.count()
    items = query.offset(offset).limit(limit).all()

    return items, total


def search_users(db: Session, query: str, limit: int) -> list[User]:
    """Ищет активных пользователей по имени/фамилии/email — для приглашения
    в проект (доступно любому авторизованному, в отличие от полного списка
    в list_users, который ADMIN-only)."""
    pattern = f"%{query.strip()}%"

    return (
        db.query(User)
        .filter(
            User.deleted_at.is_(None),
            or_(
                User.first_name.ilike(pattern),
                User.last_name.ilike(pattern),
                User.email.ilike(pattern),
            ),
        )
        .order_by(User.first_name.asc(), User.last_name.asc())
        .limit(limit)
        .all()
    )


def get_user(db: Session, user_id: int) -> User:
    """Возвращает пользователя по id.

    Бросает: NotFoundError, если пользователь не найден или удалён.
    """
    user = get_active(db, User, user_id)

    if not user:
        raise NotFoundError("User not found")

    return user


def update_role(db: Session, actor: User, user_id: int, role: str) -> User:
    """Меняет глобальную роль пользователя.

    Бросает: NotFoundError, если пользователь не найден.
    """
    target_user = get_active(db, User, user_id)

    if not target_user:
        raise NotFoundError("User not found")

    target_user.role = role

    record_audit(
        db,
        actor,
        "user.role_update",
        "user",
        target_user.id,
        {"role": role},
    )

    db.commit()
    db.refresh(target_user)

    return target_user


def update_status(db: Session, actor: User, user_id: int, is_active: bool) -> User:
    """Меняет статус активности пользователя.

    Бросает: NotFoundError, если пользователь не найден.
    """
    target_user = get_active(db, User, user_id)

    if not target_user:
        raise NotFoundError("User not found")

    target_user.is_active = is_active

    record_audit(
        db,
        actor,
        "user.status_update",
        "user",
        target_user.id,
        {"isActive": is_active},
    )

    db.commit()
    db.refresh(target_user)

    return target_user


def delete_user(db: Session, actor: User, user_id: int) -> None:
    """Удаляет пользователя (soft delete).

    Бросает: NotFoundError, если пользователь не найден.
    Бросает: LastProjectOwnerError, если пользователь — последний OWNER
    хотя бы одного проекта.
    """
    target_user = get_active(db, User, user_id)

    if not target_user:
        raise NotFoundError("User not found")

    owned_project_ids = [
        row.project_id
        for row in db.query(ProjectMember.project_id).filter(
            ProjectMember.user_id == user_id,
            ProjectMember.role == ProjectRole.OWNER,
        )
    ]

    for project_id in owned_project_ids:
        other_owners = (
            db.query(ProjectMember)
            .filter(
                ProjectMember.project_id == project_id,
                ProjectMember.role == ProjectRole.OWNER,
                ProjectMember.user_id != user_id,
            )
            .count()
        )

        if other_owners == 0:
            raise LastProjectOwnerError(
                "Cannot delete a user who is the last owner of a project"
            )

    target_user.deleted_at = datetime.now(UTC)

    record_audit(db, actor, "user.delete", "user", target_user.id)

    db.commit()
