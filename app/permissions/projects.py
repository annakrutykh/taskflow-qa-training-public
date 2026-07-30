"""Единая точка правды для проверок доступа к проектам и задачам
(CLAUDE.md, раздел 5) — роутеры не дублируют эту логику самостоятельно.

Ролевая модель проекта: OWNER > MANAGER > VIEWER (app.models.ProjectRole).
ADMIN (глобальная роль) обходит проверку членства — доступ есть всегда.

Не-участник существующего ресурса получает 404, а не 403 (ADR-07) — чтобы
не раскрывать факт существования чужого проекта/задачи.

Исполнитель задачи (Task.assignee_id), не являющийся участником проекта,
получает отдельный урезанный уровень доступа TaskAccess.ASSIGNEE —
просмотр и смена статуса задачи, без прав на остальные поля.
"""

from enum import StrEnum

from sqlalchemy.orm import Session

from app.core.errors import ForbiddenError, NotFoundError
from app.models import Project, ProjectMember, ProjectRole, Task, User

_ROLE_RANK = {
    ProjectRole.VIEWER: 0,
    ProjectRole.MANAGER: 1,
    ProjectRole.OWNER: 2,
    # ADMIN как роль в project_members — чисто информационная (см.
    # add_member/update_member_role в app.services.projects): её носитель
    # всегда одновременно глобальный ADMIN, а для него require_project_role
    # и get_task_access уже отдают полный доступ ДО обращения к этой роли
    # (см. ветку "if user.role == 'ADMIN'" ниже). Ранг нужен только чтобы
    # сравнение _ROLE_RANK[...] не падало с KeyError, если строка ADMIN
    # где-то попадёт в общий код сравнения ролей.
    ProjectRole.ADMIN: 3,
}


def get_membership(db: Session, project_id: int, user_id: int) -> ProjectMember | None:
    return db.get(ProjectMember, (project_id, user_id))


def require_project_role(
    db: Session,
    project: Project,
    user: User,
    min_role: ProjectRole,
) -> ProjectMember | None:
    """Проверяет доступ к проекту с минимальной ролью min_role.

    Бросает NotFoundError, если пользователь не участник проекта (и не
    ADMIN) — не-участнику нельзя даже узнать, что проект существует.
    Бросает ForbiddenError, если участник, но его роли недостаточно.
    Возвращает членство участника (для ADMIN — None, у него нет строки
    в project_members).
    """
    if user.role == "ADMIN":
        return None

    membership = get_membership(db, project.id, user.id)

    if membership is None:
        raise NotFoundError("Проект не найден")

    if _ROLE_RANK[membership.role] < _ROLE_RANK[min_role]:
        raise ForbiddenError("Недостаточно прав в проекте")

    return membership


class TaskAccess(StrEnum):
    NONE = "NONE"
    ASSIGNEE = "ASSIGNEE"
    VIEWER = "VIEWER"
    MANAGER = "MANAGER"


def get_task_access(db: Session, task: Task, user: User) -> TaskAccess:
    if user.role == "ADMIN":
        return TaskAccess.MANAGER

    membership = get_membership(db, task.project_id, user.id)
    is_assignee = task.assignee_id == user.id

    if membership is not None:
        if _ROLE_RANK[membership.role] >= _ROLE_RANK[ProjectRole.MANAGER]:
            return TaskAccess.MANAGER

        # VIEWER даёт только просмотр+комментарии; будучи ещё и
        # исполнителем, пользователь не должен терять право менять status
        # только из-за того, что формально состоит в проекте (иначе VIEWER
        # оказывается СТРОЖЕ, чем не-участник-исполнитель — очевидно не то,
        # что задумано).
        return TaskAccess.ASSIGNEE if is_assignee else TaskAccess.VIEWER

    return TaskAccess.ASSIGNEE if is_assignee else TaskAccess.NONE


def get_accessible_task(db: Session, task_id: int, user: User) -> Task:
    """Возвращает задачу, если у пользователя есть к ней хоть какой-то
    доступ (участник проекта любой роли, исполнитель или ADMIN).
    Иначе — NotFoundError (задача не существует, либо доступа нет —
    неразличимо, см. ADR-07)."""
    task = db.query(Task).filter(Task.id == task_id, Task.deleted_at.is_(None)).first()

    if not task:
        raise NotFoundError("Задача не найдена")

    if get_task_access(db, task, user) == TaskAccess.NONE:
        raise NotFoundError("Задача не найдена")

    return task


def require_task_manage(db: Session, task: Task, user: User) -> None:
    """Права на удаление задачи / управление метками — только участнику
    с ролью MANAGER+ или ADMIN. Просмотр уже подтверждён вызывающим кодом
    через get_accessible_task."""
    if get_task_access(db, task, user) != TaskAccess.MANAGER:
        raise ForbiddenError("Недостаточно прав")
