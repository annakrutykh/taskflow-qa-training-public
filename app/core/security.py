"""Аутентификация: разбор JWT и получение текущего пользователя (CLAUDE.md,
раздел 5 — "Core: ... безопасность"). Используется во всех роутерах через
Depends(cur)/Depends(adm) — не HTTP-специфично сверх минимального
взаимодействия с заголовком Authorization, которое требует сама схема Bearer.
"""

import logging

import jwt
import redis
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.db_utils import get_active
from app.core.errors import ForbiddenError, UnauthorizedError
from app.core.redis_client import redis_client
from app.models import User

logger = logging.getLogger("app.security")

# auto_error=False — иначе FastAPI сам бросает 403 при отсутствии
# заголовка Authorization, ещё до того как выполнится cur().
security = HTTPBearer(auto_error=False)


def _is_blacklisted(jti: str) -> bool:
    """Проверяет, отозван ли токен через POST /auth/logout.

    Fail-open: если Redis недоступен, токен считается не отозванным —
    деградация Redis не должна блокировать всех авторизованных пользователей.
    """
    try:
        return redis_client.exists(f"blacklist:{jti}") == 1
    except redis.RedisError:
        logger.warning("Redis недоступен, проверка блэклиста токена пропущена")
        return False


def build_cur(missing_credentials_error_cls=UnauthorizedError):
    """Фабрика auth-зависимости. Параметризована классом исключения для
    случая отсутствия учётных данных. Во всех остальных случаях (невалидный
    токен, деактивированный пользователь) поведение всегда 401."""

    def dependency(
        request: Request,
        c: HTTPAuthorizationCredentials | None = Depends(security),
        db: Session = Depends(get_db),
    ):
        if c is None:
            raise missing_credentials_error_cls("Not authenticated")

        try:
            payload = jwt.decode(
                c.credentials,
                settings.jwt_secret,
                algorithms=["HS256"],
            )
            user_id = int(payload["sub"])
        except (jwt.PyJWTError, ValueError, KeyError) as exc:
            raise UnauthorizedError("Invalid token") from exc

        jti = payload.get("jti")
        if jti and _is_blacklisted(jti):
            raise UnauthorizedError("Token has been revoked")

        user = get_active(db, User, user_id)

        if not user or not user.is_active:
            raise UnauthorizedError("Inactive user")

        request.state.user_id = user.id
        request.state.username = user.email
        request.state.jwt_jti = jti
        request.state.jwt_exp = payload.get("exp")

        return user

    return dependency


cur = build_cur()


def adm(
    user=Depends(cur),
):
    if user.role != "ADMIN":
        raise ForbiddenError("Admin required")

    return user
