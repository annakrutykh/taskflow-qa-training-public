"""Бизнес-логика управления пользователями (CLAUDE.md, раздел 5)."""

from datetime import UTC, datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.audit import record_audit
from app.core.db_utils import get_active
from app.core.defects import defects
from app.core.errors import (
    LastAdminError,
    LastProjectOwnerError,
    MaxAdminsError,
    NotFoundError,
)
from app.models import Project, ProjectMember, ProjectRole, User

MAX_ADMINS = 3


def _other_active_admin_count(db: Session, user_id: int) -> int:
    return (
        db.query(User)
        .filter(
            User.role == "ADMIN",
            User.is_active.is_(True),
            User.deleted_at.is_(None),
            User.id != user_id,
        )
        .count()
    )


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
    в проект или выбора исполнителя задачи (доступно любому авторизованному,
    в отличие от полного списка в list_users, который ADMIN-only).

    D-19: по умолчанию запрос из одних пробельных символов схлопывается
    после .strip() в пустую строку — ILIKE-паттерн "%%" матчит всех
    пользователей, отдавая по факту список уровня ADMIN-only GET /users
    любому авторизованному. При отключённом дефекте такой запрос вместо
    этого возвращает пустой список.
    """
    stripped = query.strip()

    if not defects.is_enabled("D-19") and not stripped:
        return []

    pattern = f"%{stripped}%"

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
        raise NotFoundError("Пользователь не найден")

    return user


def update_role(db: Session, actor: User, user_id: int, role: str) -> User:
    """Меняет глобальную роль пользователя.

    Бросает: NotFoundError, если пользователь не найден.
    Бросает: LastAdminError, если это последний активный ADMIN, а роль
    меняется на не-ADMIN.
    Бросает: MaxAdminsError, если роль меняется на ADMIN, а лимит
    активных админов (MAX_ADMINS) уже достигнут.
    """
    target_user = get_active(db, User, user_id)

    if not target_user:
        raise NotFoundError("Пользователь не найден")

    if (
        target_user.role == "ADMIN"
        and target_user.is_active
        and role != "ADMIN"
        and _other_active_admin_count(db, user_id) == 0
    ):
        raise LastAdminError("Нельзя разжаловать последнего активного администратора")

    if (
        target_user.role != "ADMIN"
        and role == "ADMIN"
        and _other_active_admin_count(db, user_id) >= MAX_ADMINS
    ):
        raise MaxAdminsError(
            f"Нельзя одновременно иметь более {MAX_ADMINS} активных администраторов"
        )

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
    Бросает: LastAdminError, если это последний активный ADMIN, а статус
    меняется на неактивный.
    """
    target_user = get_active(db, User, user_id)

    if not target_user:
        raise NotFoundError("Пользователь не найден")

    if (
        not is_active
        and target_user.role == "ADMIN"
        and target_user.is_active
        and _other_active_admin_count(db, user_id) == 0
    ):
        raise LastAdminError(
            "Нельзя деактивировать последнего активного администратора"
        )

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
    Бросает: LastAdminError, если пользователь — последний активный ADMIN.
    Бросает: LastProjectOwnerError, если пользователь — последний OWNER
    хотя бы одного проекта.
    """
    target_user = get_active(db, User, user_id)

    if not target_user:
        raise NotFoundError("Пользователь не найден")

    if (
        target_user.role == "ADMIN"
        and target_user.is_active
        and _other_active_admin_count(db, user_id) == 0
    ):
        raise LastAdminError("Нельзя удалить последнего активного администратора")

    # Join на Project и фильтр deleted_at обязателен: у мягко удалённого
    # проекта строки в project_members не чистятся (см. delete_project),
    # без этого фильтра пользователя нельзя удалить из-за проекта, которого
    # уже фактически не существует.
    owned_project_ids = [
        row.project_id
        for row in db.query(ProjectMember.project_id)
        .join(Project, Project.id == ProjectMember.project_id)
        .filter(
            ProjectMember.user_id == user_id,
            ProjectMember.role == ProjectRole.OWNER,
            Project.deleted_at.is_(None),
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
                "Нельзя удалить пользователя — он последний владелец проекта"
            )

    target_user.deleted_at = datetime.now(UTC)

    record_audit(db, actor, "user.delete", "user", target_user.id)

    db.commit()
