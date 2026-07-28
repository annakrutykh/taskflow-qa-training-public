from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import adm
from app.services.admin import reset_database as reset_database_service

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post(
    "/reset",
    status_code=204,
    summary="Сбросить базу данных",
    description="Полностью очищает все данные и заново заполняет их "
    "из seed.py. Только для администратора. Необратимо.",
    responses={
        204: {"description": "База данных сброшена и заполнена заново"},
        403: {"description": "Недостаточно прав"},
    },
)
def reset_database(
    user=Depends(adm),
    db: Session = Depends(get_db),
):
    reset_database_service(db, user)

    return Response(status_code=204)
