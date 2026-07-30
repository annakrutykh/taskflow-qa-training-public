from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import cur
from app.schemas import (
    Page,
    TaskCreate,
    TaskPriority,
    TaskResponse,
    TaskStatus,
    TaskUpdate,
)
from app.services.tasks import (
    TASK_LIST_RESPONSE_EXCLUDE,
    TASK_RESPONSE_EXCLUDE,
    create_task,
    get_task,
    list_tasks,
)
from app.services.tasks import (
    delete_task as delete_task_service,
)
from app.services.tasks import (
    update_task as update_task_service,
)

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post(
    "",
    response_model=TaskResponse,
    response_model_exclude=TASK_RESPONSE_EXCLUDE,
    status_code=201,
    summary="Создать задачу",
    description="Создает новую задачу в проекте. "
    "Доступ — участник проекта с ролью MANAGER+ или ADMIN.",
)
def add_task(
    body: TaskCreate,
    response: Response,
    user=Depends(cur),
    db: Session = Depends(get_db),
):
    task = create_task(
        db,
        user,
        body.projectId,
        body.title,
        body.description,
        body.priority,
        body.assigneeId,
    )

    response.headers["Location"] = f"/api/v1/tasks/{task.id}"

    return task


@router.get(
    "",
    response_model=Page[TaskResponse],
    response_model_exclude=TASK_LIST_RESPONSE_EXCLUDE,
    summary="Получить задачи",
    description="Возвращает задачи из проектов, где пользователь участник, "
    "плюс задачи, назначенные на него напрямую. ADMIN видит все задачи.",
)
def tasks(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: TaskStatus | None = None,
    priority: TaskPriority | None = None,
    assigneeId: int | None = None,
    projectId: int | None = None,
    search: str | None = None,
    sort: str | None = None,
    order: str = Query(
        "asc",
        pattern="^(asc|desc)$",
    ),
    user=Depends(cur),
    db: Session = Depends(get_db),
):
    items, total = list_tasks(
        db,
        user,
        limit,
        offset,
        status,
        priority,
        assigneeId,
        projectId,
        search,
        sort,
        order,
    )

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "hasNext": offset + len(items) < total,
    }


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    response_model_exclude=TASK_RESPONSE_EXCLUDE,
    summary="Получить задачу",
    description="Возвращает информацию о задаче по идентификатору. Доступ — "
    "участник проекта любой роли, исполнитель задачи или ADMIN.",
    responses={
        200: {"description": "Задача найдена"},
        404: {"description": "Задача не найдена"},
    },
)
def get_task_endpoint(
    task_id: int,
    user=Depends(cur),
    db: Session = Depends(get_db),
):
    return get_task(db, user, task_id)


@router.patch(
    "/{task_id}",
    response_model=TaskResponse,
    response_model_exclude=TASK_RESPONSE_EXCLUDE,
    summary="Обновить задачу",
    description="Обновляет поля существующей задачи. Участник с ролью "
    "MANAGER+ может менять любые поля; исполнитель без членства в проекте — "
    "только status.",
    responses={
        200: {"description": "Задача обновлена"},
        403: {"description": "Недостаточно прав"},
        404: {"description": "Задача не найдена"},
    },
)
def update_task(
    task_id: int,
    body: TaskUpdate,
    user=Depends(cur),
    db: Session = Depends(get_db),
):
    provided_fields = body.model_dump(exclude_unset=True)

    return update_task_service(db, user, task_id, provided_fields)


@router.delete(
    "/{task_id}",
    status_code=204,
    summary="Удалить задачу",
    description="Удаляет задачу. Доступ — участник проекта с ролью MANAGER+ или ADMIN.",
    responses={
        204: {"description": "Задача удалена"},
        403: {"description": "Недостаточно прав"},
        404: {"description": "Задача не найдена"},
    },
)
def delete_task(
    task_id: int,
    user=Depends(cur),
    db: Session = Depends(get_db),
):
    delete_task_service(db, user, task_id)

    return Response(
        status_code=204,
    )
