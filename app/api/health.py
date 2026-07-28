from fastapi import APIRouter, Depends, Response
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import get_db

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    summary="Проверка живости процесса",
    description="Всегда 200, если процесс api способен отвечать на HTTP.",
)
def health():
    return {"status": "ok"}


@router.get(
    "/ready",
    summary="Проверка готовности",
    description="200, если приложение может выполнить запрос к БД.",
)
def ready(response: Response, db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        response.status_code = 503
        return {"status": "unavailable"}

    return {"status": "ok"}
