from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import adm, cur
from app.schemas import (
    Page,
    UserResponse,
    UserRoleUpdate,
    UserSearchResult,
    UserStatusUpdate,
    UserUpdate,
)
from app.services.users import (
    delete_user as delete_user_service,
)
from app.services.users import (
    get_user as get_user_service,
)
from app.services.users import (
    list_users,
    search_users,
    update_own_profile,
    update_role,
    update_status,
)

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Получить текущего пользователя",
    description="Возвращает информацию об авторизованном пользователе.",
    responses={
        200: {"description": "Информация получена"},
        401: {"description": "Не авторизован"},
    },
)
def me(
    user=Depends(cur),
):
    return user


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Обновить профиль",
    description="Обновляет имя и фамилию текущего пользователя.",
    responses={
        200: {"description": "Профиль обновлен"},
        401: {"description": "Не авторизован"},
    },
)
def patch_me(
    body: UserUpdate,
    user=Depends(cur),
    db: Session = Depends(get_db),
):
    return update_own_profile(db, user, body.firstName, body.lastName)


@router.get(
    "",
    response_model=Page[UserResponse],
    summary="Получить список пользователей",
    description="Возвращает список пользователей. Только для администратора.",
)
def users(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _=Depends(adm),
    db: Session = Depends(get_db),
):
    items, total = list_users(db, limit, offset)

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "hasNext": offset + len(items) < total,
    }


@router.get(
    "/search",
    response_model=list[UserSearchResult],
    summary="Найти пользователя по имени/email",
    description="Доступно любому авторизованному пользователю (в отличие от "
    "полного списка GET /users) — минимальный набор полей, без роли и "
    "статуса, чтобы пригласить нужного человека в проект по имени.",
    responses={
        200: {"description": "Результаты поиска (может быть пустым)"},
        401: {"description": "Не авторизован"},
    },
)
def search_users_endpoint(
    q: str = Query(..., min_length=1, max_length=100),
    limit: int = Query(20, ge=1, le=50),
    _=Depends(cur),
    db: Session = Depends(get_db),
):
    return search_users(db, q, limit)


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Получить пользователя",
    description="Возвращает информацию о пользователе по идентификатору.",
    responses={
        200: {"description": "Пользователь найден"},
        404: {"description": "Пользователь не найден"},
    },
)
def get_user(
    user_id: int,
    _=Depends(adm),
    db: Session = Depends(get_db),
):
    return get_user_service(db, user_id)


@router.patch(
    "/{user_id}/role",
    response_model=UserResponse,
    summary="Изменить роль пользователя",
    description="Изменяет роль пользователя.",
    responses={
        200: {"description": "Роль изменена"},
        404: {"description": "Пользователь не найден"},
    },
)
def update_role_endpoint(
    user_id: int,
    body: UserRoleUpdate,
    user=Depends(adm),
    db: Session = Depends(get_db),
):
    return update_role(db, user, user_id, body.role)


@router.patch(
    "/{user_id}/status",
    response_model=UserResponse,
    summary="Изменить статус пользователя",
    description="Изменяет статус активности пользователя.",
    responses={
        200: {"description": "Статус обновлен"},
        404: {"description": "Пользователь не найден"},
    },
)
def update_status_endpoint(
    user_id: int,
    body: UserStatusUpdate,
    user=Depends(adm),
    db: Session = Depends(get_db),
):
    return update_status(db, user, user_id, body.is_active)


@router.delete(
    "/{user_id}",
    status_code=204,
    summary="Удалить пользователя",
    description="Удаляет пользователя (soft delete). Нельзя удалить "
    "единственного OWNER какого-либо проекта.",
    responses={
        204: {"description": "Пользователь удален"},
        404: {"description": "Пользователь не найден"},
        409: {"description": "Пользователь — последний OWNER одного из проектов"},
    },
)
def delete_user_endpoint(
    user_id: int,
    user=Depends(adm),
    db: Session = Depends(get_db),
):
    delete_user_service(db, user, user_id)

    return Response(status_code=204)
