"""Обёртка над Redis для кэширования GET-ответов (CLAUDE.md, раздел 5 —
Core: инфраструктура).

Используется get_project (app/services/projects.py) — единственное место в
API, где кэш безопасен без риска показать пользователю данные, до которых
он не должен был бы добраться: набор полей ProjectResponse одинаков для
всех, кому вообще разрешено видеть проект, и не зависит от роли
конкретного вызывающего — права доступа при этом всё равно проверяются
на каждый запрос (см. require_project_role), кэшируется только сам факт
существования и содержимое проекта.

Fail-open: недоступность Redis не должна ронять запрос — при ошибке кэш
просто не используется, как и в rate_limit.py/security.py.
"""

import json
import logging

import redis

from app.core.redis_client import redis_client

logger = logging.getLogger("app.cache")


def cache_get(key: str) -> dict | None:
    try:
        raw = redis_client.get(key)
    except redis.RedisError:
        logger.warning("Redis недоступен, чтение кэша %s пропущено", key)
        return None

    return json.loads(raw) if raw is not None else None


def cache_set(key: str, value: dict, ttl_seconds: int) -> None:
    try:
        redis_client.setex(key, ttl_seconds, json.dumps(value))
    except redis.RedisError:
        logger.warning("Redis недоступен, запись в кэш %s пропущена", key)


def cache_delete(key: str) -> None:
    try:
        redis_client.delete(key)
    except redis.RedisError:
        logger.warning("Redis недоступен, инвалидация кэша %s пропущена", key)
