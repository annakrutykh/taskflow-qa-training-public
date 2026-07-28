from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import cur
from app.schemas import (
    Page,
    ProjectCreate,
    ProjectMemberCreate,
    ProjectMemberResponse,
    ProjectMemberRoleUpdate,
    ProjectResponse,
    ProjectUpdate,
)
from app.services.projects import (
    add_member,
    create_project,
    get_project,
    list_members,
    list_projects,
    remove_member,
    update_member_role,
)
from app.services.projects import (
    delete_project as delete_project_service,
)
from app.services.projects import (
    update_project as update_project_service,
)

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=201,
    summary="Создать проект",
    description="Создает новый проект для текущего пользователя. Создатель "
    "автоматически становится участником с ролью OWNER.",
    responses={
        201: {"description": "Проект успешно создан"},
        401: {"description": "Пользователь не авторизован"},
    },
)
def add_project(
    body: ProjectCreate,
    response: Response,
    user=Depends(cur),
    db: Session = Depends(get_db),
):
    project = create_project(db, user, body.name, body.description)

    response.headers["Location"] = f"/api/v1/projects/{project.id}"

    return project


@router.get(
    "",
    response_model=Page[ProjectResponse],
    summary="Получить проекты",
    description="Возвращает проекты, в которых текущий пользователь состоит "
    "участником (любая роль). ADMIN получает все проекты.",
    responses={
        200: {"description": "Список проектов"},
        401: {"description": "Пользователь не авторизован"},
    },
)
def get_projects(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user=Depends(cur),
    db: Session = Depends(get_db),
):
    items, total = list_projects(db, user, limit, offset)

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "hasNext": offset + len(items) < total,
    }


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Получить проект",
    description="Возвращает информацию о проекте. "
    "Доступ — участник любой роли или ADMIN.",
    responses={
        200: {"description": "Проект найден"},
        404: {"description": "Проект не найден"},
    },
)
def get_project_endpoint(
    project_id: int,
    user=Depends(cur),
    db: Session = Depends(get_db),
):
    return get_project(db, user, project_id)


@router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Обновить проект",
    description="Обновляет name/description/status. "
    "Доступ — участник с ролью MANAGER+ или ADMIN.",
    responses={
        200: {"description": "Проект обновлен"},
        403: {"description": "Недостаточно прав"},
        404: {"description": "Проект не найден"},
    },
)
def update_project(
    project_id: int,
    body: ProjectUpdate,
    user=Depends(cur),
    db: Session = Depends(get_db),
):
    changed_fields = body.model_dump(exclude_unset=True)

    return update_project_service(db, user, project_id, changed_fields)


@router.delete(
    "/{project_id}",
    status_code=204,
    summary="Удалить проект",
    description="Удаляет проект (soft delete, каскадно на его задачи и их "
    "комментарии). Доступ — только OWNER или ADMIN.",
    responses={
        204: {"description": "Проект удален"},
        403: {"description": "Недостаточно прав"},
        404: {"description": "Проект не найден"},
    },
)
def delete_project(
    project_id: int,
    user=Depends(cur),
    db: Session = Depends(get_db),
):
    delete_project_service(db, user, project_id)

    return Response(status_code=204)


@router.post(
    "/{project_id}/members",
    response_model=ProjectMemberResponse,
    status_code=201,
    summary="Добавить участника проекта",
    description="Добавляет пользователя в проект с указанной ролью. "
    "Доступ — только OWNER или ADMIN.",
    responses={
        201: {"description": "Участник добавлен"},
        403: {"description": "Недостаточно прав"},
        404: {"description": "Проект или пользователь не найден"},
        409: {"description": "Пользователь уже участник проекта"},
    },
)
def add_project_member(
    project_id: int,
    body: ProjectMemberCreate,
    response: Response,
    user=Depends(cur),
    db: Session = Depends(get_db),
):
    membership = add_member(db, user, project_id, body.userId, body.role)

    response.headers["Location"] = (
        f"/api/v1/projects/{project_id}/members/{body.userId}"
    )

    return membership


@router.get(
    "/{project_id}/members",
    response_model=Page[ProjectMemberResponse],
    summary="Получить участников проекта",
    description="Возвращает список участников проекта. "
    "Доступ — любой участник проекта или ADMIN.",
    responses={
        200: {"description": "Список участников"},
        404: {"description": "Проект не найден"},
    },
)
def get_project_members(
    project_id: int,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user=Depends(cur),
    db: Session = Depends(get_db),
):
    items, total = list_members(db, user, project_id, limit, offset)

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "hasNext": offset + len(items) < total,
    }


@router.patch(
    "/{project_id}/members/{user_id}",
    response_model=ProjectMemberResponse,
    summary="Изменить роль участника",
    description="Доступ — только OWNER или ADMIN. Нельзя разжаловать последнего OWNER.",
    responses={
        200: {"description": "Роль изменена"},
        403: {"description": "Недостаточно прав"},
        404: {"description": "Проект или участник не найден"},
        409: {"description": "Нельзя разжаловать последнего OWNER"},
    },
)
def update_project_member_role(
    project_id: int,
    user_id: int,
    body: ProjectMemberRoleUpdate,
    user=Depends(cur),
    db: Session = Depends(get_db),
):
    return update_member_role(db, user, project_id, user_id, body.role)


@router.delete(
    "/{project_id}/members/{user_id}",
    status_code=204,
    summary="Удалить участника проекта",
    description="Доступ — только OWNER или ADMIN. Нельзя удалить последнего OWNER.",
    responses={
        204: {"description": "Участник удален"},
        403: {"description": "Недостаточно прав"},
        404: {"description": "Проект или участник не найден"},
        409: {"description": "Нельзя удалить последнего OWNER"},
    },
)
def delete_project_member(
    project_id: int,
    user_id: int,
    user=Depends(cur),
    db: Session = Depends(get_db),
):
    remove_member(db, user, project_id, user_id)

    return Response(status_code=204)
