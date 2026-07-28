"""Клиент Redis (CLAUDE.md, раздел 5 — Core: инфраструктура).

Используется rate limiting'ом (app/core/rate_limit.py) и блэклистом JWT
(app/core/security.py, app/services/auth.py). Один общий пул соединений на
процесс — как и SessionLocal для БД.
"""

import redis

from app.core.config import settings

redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
