from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.defects import defects
from app.core.errors import ForbiddenError
from app.core.security import adm, build_cur, cur
from app.schemas import (
    LabelCreate,
    LabelResponse,
    Page,
)
from app.services.labels import (
    attach_label as attach_label_service,
)
from app.services.labels import (
    create_label as create_label_service,
)
from app.services.labels import (
    delete_label as delete_label_service,
)
from app.services.labels import (
    detach_label as detach_label_service,
)
from app.services.labels import (
    list_labels,
)

router = APIRouter(tags=["Labels"])

_get_labels_cur = build_cur(ForbiddenError) if defects.is_enabled("D-02") else cur


@router.post(
    "/labels",
    response_model=LabelResponse,
    status_code=201,
    summary="Создать метку",
    description="Создает новую метку. Только для администратора.",
)
def create_label(
    body: LabelCreate,
    response: Response,
    user=Depends(adm),
    db: Session = Depends(get_db),
):
    label = create_label_service(db, user, body.name)

    response.headers["Location"] = f"/api/v1/labels/{label.id}"

    return label


@router.get(
    "/labels",
    response_model=Page[LabelResponse],
    summary="Получить список меток",
    description="Возвращает список всех доступных меток.",
    responses={
        200: {"description": "Список меток получен"},
        401: {"description": "Пользователь не авторизован"},
    },
)
def get_labels(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _=Depends(_get_labels_cur),
    db: Session = Depends(get_db),
):
    items, total = list_labels(db, limit, offset)

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "hasNext": offset + len(items) < total,
    }


@router.post(
    "/tasks/{task_id}/labels/{label_id}",
    status_code=204,
    summary="Добавить метку к задаче",
    description="Привязывает существующую метку к задаче.",
    responses={
        204: {"description": "Метка успешно добавлена"},
        403: {"description": "Недостаточно прав"},
        404: {"description": "Задача или метка не найдена"},
    },
)
def attach_label(
    task_id: int,
    label_id: int,
    user=Depends(cur),
    db: Session = Depends(get_db),
):
    attach_label_service(db, user, task_id, label_id)

    return Response(
        status_code=204,
    )


@router.delete(
    "/tasks/{task_id}/labels/{label_id}",
    status_code=204,
    summary="Отвязать метку от задачи",
    description="Отвязывает метку от задачи. Доступ — участник проекта с "
    "ролью MANAGER+ или ADMIN. Идемпотентно.",
    responses={
        204: {"description": "Метка отвязана (или уже не была привязана)"},
        403: {"description": "Недостаточно прав"},
        404: {"description": "Задача не найдена"},
    },
)
def detach_label(
    task_id: int,
    label_id: int,
    user=Depends(cur),
    db: Session = Depends(get_db),
):
    detach_label_service(db, user, task_id, label_id)

    return Response(status_code=204)


@router.delete(
    "/labels/{label_id}",
    status_code=204,
    summary="Удалить метку",
    description="Удаляет метку целиком (и её привязки ко всем задачам). "
    "Только для администратора.",
    responses={
        204: {"description": "Метка удалена"},
        403: {"description": "Недостаточно прав"},
        404: {"description": "Метка не найдена"},
    },
)
def delete_label(
    label_id: int,
    user=Depends(adm),
    db: Session = Depends(get_db),
):
    delete_label_service(db, user, label_id)

    return Response(status_code=204)
