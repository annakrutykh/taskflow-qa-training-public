"""Общие фикстуры для всего тестового набора.

Почему без testcontainers, хотя CLAUDE.md (раздел 10) называет его для
tests/integration/: тесты обязаны выполняться под Python 3.12 (хостовый
Python 3.14 не может собрать psycopg2 из исходников — см.
docs/internal/KNOWN_DEFECTS.md/S0), то есть внутри контейнера. Внутри него
testcontainers поднимал бы сиблинг-контейнер Postgres через docker socket
(Docker-outside-of-Docker) — а это сетевые нюансы (localhost внутри
контейнера ≠ localhost хоста, нужен reaper-контейнер и т.д.), рискованные
без интерактивной отладки. Решение (согласовано с владельцем проекта):
тесты подключаются к уже поднятому `db` из docker-compose.yml по имени
хоста `db` — тот же Postgres 16, та же схема через реальный Alembic,
просто без отдельного эфемерного контейнера на тест-сессию. Это даёт
интеграционные тесты с реальным PostgreSQL, как и требуется, только без
слоя testcontainers поверх него.

Запуск — см. docs/TESTING.md (`make smoke`/`make integration`/
`make regression`), либо вручную (контейнер должен быть в сети
docker-compose, `db` и `redis` обязательны поднятыми; requirements-dev уже
в образе — не нужно ставить на каждый запуск, см. Dockerfile):
    docker compose up -d db redis
    docker run --rm -v "$(pwd):/app" -w /app --network taskflow-main_default \
        -e DATABASE_URL=postgresql://taskflow:taskflow@db:5432/taskflow \
        -e REDIS_URL=redis://redis:6379/0 \
        taskflow-main-api sh -c "pytest"

Лимиты rate limiting (app/core/rate_limit.py) по умолчанию для тестов
выставлены очень высокими — иначе `admin_token`, вызывающий реальный
POST /auth/login на каждый тест, довольно быстро упёрся бы в лимит.
Тест самого rate limiting (tests/integration/test_rate_limit.py)
переопределяет лимит точечно через monkeypatch.setenv().
"""

import os
import subprocess
import uuid

os.environ.setdefault("DATABASE_URL", "postgresql://taskflow:taskflow@db:5432/taskflow")
os.environ.setdefault("REDIS_URL", "redis://redis:6379/0")
os.environ.setdefault("RATE_LIMIT_LOGIN_MAX_ATTEMPTS", "100000")
os.environ.setdefault("RATE_LIMIT_REGISTER_MAX_ATTEMPTS", "100000")
# Elasticsearch — тяжёлая инфраструктура, не нужна для pytest (см. docs/TESTING.md):
# отправку логов в ES проверяем вручную через docker compose, не в тестах.
os.environ.setdefault("ELASTICSEARCH_ENABLED", "false")
# TRAINING_DEFECTS_DISABLED — чёрный список (app/core/defects.py), пустое
# значение означает "не выключено ничего", т.е. все учебные дефекты
# активны. Тестовый набор — регрессия против docs/API_SPEC.md, поэтому
# ему всегда нужно "ALL": сам он дефект точечно не воспроизводит
# (см. tests/integration/test_defects_regression.py).
os.environ.setdefault("TRAINING_DEFECTS_DISABLED", "ALL")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.core.database import SessionLocal  # noqa: E402
from app.core.redis_client import redis_client  # noqa: E402
from app.core.seed import seed_database  # noqa: E402
from app.main import app  # noqa: E402
from app.services.admin import _TABLES  # noqa: E402


@pytest.fixture(scope="session")
def _prepare_database():
    """Один раз на тестовую сессию: накатывает миграции и приводит БД к
    чистому seed-состоянию. Отдельные тесты создают свои изолированные
    данные поверх этого (случайные email и т.п.), а не полагаются на
    порядок выполнения друг друга (CLAUDE.md, раздел 10).

    НЕ autouse: только тесты, которым реально нужна БД (через фикстуру
    client), должны её требовать — иначе tests/unit/ перестанут быть
    "без БД" (CLAUDE.md, раздел 10) при обычном запуске `pytest`."""
    subprocess.run(["alembic", "upgrade", "head"], check=True)

    db = SessionLocal()
    try:
        db.execute(
            text(f"TRUNCATE TABLE {', '.join(_TABLES)} RESTART IDENTITY CASCADE")
        )
        db.commit()
        seed_database(db)
        db.commit()
    finally:
        db.close()


@pytest.fixture(scope="session")
def client(_prepare_database):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def clean_redis():
    """Чистит ключи rate limit/blacklist до и после теста — для тестов,
    которым нужен предсказуемый счётчик (свои же прошлые запросы в рамках
    сессии не должны накапливаться)."""
    keys = redis_client.keys("rate_limit:*") + redis_client.keys("blacklist:*")
    if keys:
        redis_client.delete(*keys)
    yield
    keys = redis_client.keys("rate_limit:*") + redis_client.keys("blacklist:*")
    if keys:
        redis_client.delete(*keys)


def unique_email() -> str:
    return f"test-{uuid.uuid4().hex[:12]}@example.com"


def register_and_login(client: TestClient, password: str = "Password123!") -> dict:
    """Регистрирует нового пользователя со случайным email и логинит его.
    Возвращает {"user": <UserResponse dict>, "token": <accessToken>,
    "email": ..., "password": ...} — изолировано от других тестов и от
    сидированных данных."""
    email = unique_email()

    register_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "firstName": "Test",
            "lastName": "User",
        },
    )
    assert register_resp.status_code == 201, register_resp.text

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_resp.status_code == 200, login_resp.text

    return {
        "user": register_resp.json(),
        "token": login_resp.json()["accessToken"],
        "email": email,
        "password": password,
    }


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_token(client: TestClient) -> str:
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "Admin123!"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["accessToken"]


def create_project(client: TestClient, token: str, name: str = "Test Project") -> int:
    resp = client.post(
        "/api/v1/projects",
        json={"name": name},
        headers=auth_headers(token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def add_member(
    client: TestClient,
    owner_token: str,
    project_id: int,
    user_id: int,
    role: str = "VIEWER",
) -> dict:
    resp = client.post(
        f"/api/v1/projects/{project_id}/members",
        json={"userId": user_id, "role": role},
        headers=auth_headers(owner_token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def create_task(
    client: TestClient, token: str, project_id: int, title: str = "Test task", **extra
) -> dict:
    body = {"projectId": project_id, "title": title, **extra}
    resp = client.post("/api/v1/tasks", json=body, headers=auth_headers(token))
    assert resp.status_code == 201, resp.text
    return resp.json()
