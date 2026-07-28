from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import cur
from app.schemas import (
    CommentCreate,
    CommentResponse,
    CommentUpdate,
    Page,
)
from app.services.comments import (
    create_comment,
    list_comments,
)
from app.services.comments import (
    delete_comment as delete_comment_service,
)
from app.services.comments import (
    update_comment as update_comment_service,
)

router = APIRouter(prefix="/tasks/{task_id}/comments", tags=["Comments"])


@router.post(
    "",
    response_model=CommentResponse,
    status_code=201,
    summary="Добавить комментарий",
    description="Добавляет комментарий к задаче.",
    responses={
        201: {"description": "Комментарий создан"},
        404: {"description": "Задача не найдена"},
    },
)
def add_comment(
    task_id: int,
    body: CommentCreate,
    response: Response,
    user=Depends(cur),
    db: Session = Depends(get_db),
):
    comment = create_comment(db, user, task_id, body.text)

    response.headers["Location"] = f"/api/v1/tasks/{task_id}/comments/{comment.id}"

    return comment


@router.get(
    "",
    response_model=Page[CommentResponse],
    summary="Получить комментарии",
    description="Возвращает список комментариев задачи.",
)
def get_comments(
    task_id: int,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user=Depends(cur),
    db: Session = Depends(get_db),
):
    items, total = list_comments(db, user, task_id, limit, offset)

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "hasNext": offset + len(items) < total,
    }


@router.patch(
    "/{comment_id}",
    response_model=CommentResponse,
    summary="Изменить комментарий",
    description="Доступ — только автор комментария.",
    responses={
        200: {"description": "Комментарий обновлен"},
        403: {"description": "Не автор комментария"},
        404: {"description": "Задача или комментарий не найден"},
    },
)
def update_comment(
    task_id: int,
    comment_id: int,
    body: CommentUpdate,
    user=Depends(cur),
    db: Session = Depends(get_db),
):
    return update_comment_service(db, user, task_id, comment_id, body.text)


@router.delete(
    "/{comment_id}",
    status_code=204,
    summary="Удалить комментарий",
    description="Доступ — автор комментария либо участник проекта "
    "с ролью MANAGER+/ADMIN.",
    responses={
        204: {"description": "Комментарий удален"},
        403: {"description": "Недостаточно прав"},
        404: {"description": "Задача или комментарий не найден"},
    },
)
def delete_comment(
    task_id: int,
    comment_id: int,
    user=Depends(cur),
    db: Session = Depends(get_db),
):
    delete_comment_service(db, user, task_id, comment_id)

    return Response(status_code=204)
