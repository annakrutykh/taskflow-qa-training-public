"""Rate limiting на основе Redis для чувствительных к перебору ручек
(CLAUDE.md, раздел 5 — Core: инфраструктура).

Фиксированное окно (fixed window): счётчик по ключу растёт на каждый запрос
и живёт `window_seconds` с момента первого запроса в окне. Лимит и окно
читаются из переменных окружения на каждый вызов (а не один раз при
старте) — это осознанно, чтобы тесты могли переопределять их через
monkeypatch.setenv() без перезапуска приложения.

Fail-open: если Redis недоступен, запрос пропускается без ограничения —
для auth-ручек доступность важнее защиты от перебора, деградация Redis не
должна блокировать вход в систему.
"""

import logging
import os

import redis
from fastapi import Request

from app.core.errors import TooManyRequestsError
from app.core.redis_client import redis_client

logger = logging.getLogger("app.rate_limit")


def rate_limit(
    action: str,
    env_prefix: str,
    default_max_attempts: int,
    default_window_seconds: int,
):
    """Фабрика FastAPI-зависимости, ограничивающей число запросов на один
    client IP в окне времени. `env_prefix` задаёт имена переменных
    окружения: `{env_prefix}_MAX_ATTEMPTS`, `{env_prefix}_WINDOW_SECONDS`.

    Бросает: TooManyRequestsError (429, с заголовком Retry-After), если
    лимит превышен.
    """

    def dependency(request: Request) -> None:
        max_attempts = int(
            os.getenv(f"{env_prefix}_MAX_ATTEMPTS", str(default_max_attempts))
        )
        window_seconds = int(
            os.getenv(f"{env_prefix}_WINDOW_SECONDS", str(default_window_seconds))
        )
        client_ip = request.client.host if request.client else "unknown"
        key = f"rate_limit:{action}:{client_ip}"

        try:
            attempts = redis_client.incr(key)
            if attempts == 1:
                redis_client.expire(key, window_seconds)
            retry_after = redis_client.ttl(key)
        except redis.RedisError:
            logger.warning("Redis недоступен, rate limit для %s пропущен", action)
            return

        if attempts > max_attempts:
            raise TooManyRequestsError(
                f"Too many {action} attempts, try again later",
                headers={"Retry-After": str(max(retry_after, 1))},
            )

    return dependency
