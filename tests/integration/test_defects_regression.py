"""Регрессионный набор, обязательный по CLAUDE.md (раздел 10): тестовый
процесс выставляет TRAINING_DEFECTS_DISABLED=ALL (см. tests/conftest.py) —
это единственный способ выключить все дефекты разом, т.к. пустой чёрный
список ничего не выключает (дефекты активны по умолчанию). Здесь проверяем,
что при ALL ни один из намеренных дефектов не воспроизводится.

Проверку обратной ветки (дефект НЕ в чёрном списке -> воспроизводится) не
автоматизируем здесь: app.core.defects.defects читает
TRAINING_DEFECTS_DISABLED один раз при импорте процесса, так что для другой
ветки нужен отдельный процесс с иной переменной окружения — это уже
проверено вручную в S5 (см. docs/internal/KNOWN_DEFECTS.md, раздел D) и
остаётся ручной операцией до тех пор, пока не появится параметризация
тестового процесса по окружению."""

import logging

from tests.conftest import (
    auth_headers,
    create_project,
    create_task,
    register_and_login,
    unique_email,
)


def test_d01_priority_sort_is_logical_by_default(client):
    owner = register_and_login(client)
    project_id = create_project(client, owner["token"])
    create_task(client, owner["token"], project_id, title="h", priority="HIGH")
    create_task(client, owner["token"], project_id, title="l", priority="LOW")
    create_task(client, owner["token"], project_id, title="m", priority="MEDIUM")

    resp = client.get(
        f"/api/v1/tasks?projectId={project_id}&sort=priority&order=asc",
        headers=auth_headers(owner["token"]),
    )

    priorities = [t["priority"] for t in resp.json()["items"]]
    assert priorities == ["LOW", "MEDIUM", "HIGH"]


def test_d02_labels_without_token_is_401_not_403(client):
    resp = client.get("/api/v1/labels")

    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


def test_d04_labels_field_present_in_task_response(client):
    owner = register_and_login(client)
    project_id = create_project(client, owner["token"])
    task = create_task(client, owner["token"], project_id)

    resp = client.get(
        f"/api/v1/tasks/{task['id']}", headers=auth_headers(owner["token"])
    )

    assert "labels" in resp.json()


def test_d03_email_uniqueness_is_case_insensitive_by_default(client):
    email = unique_email()
    payload = {
        "email": email,
        "password": "Password123!",
        "firstName": "A",
        "lastName": "B",
    }

    first = client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 201

    second = client.post(
        "/api/v1/auth/register",
        json={**payload, "email": email.upper()},
    )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"


def test_d17_password_never_appears_in_logs(client, caplog):
    account = register_and_login(client, password="SuperSecret123!")

    with caplog.at_level(logging.DEBUG):
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": account["email"], "password": "SuperSecret123!"},
        )

    assert resp.status_code == 200
    for record in caplog.records:
        assert "SuperSecret123!" not in record.getMessage()


def test_d18_empty_password_is_validation_error_by_default(client):
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": unique_email(), "password": ""},
    )

    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_d19_whitespace_only_search_returns_empty_by_default(client):
    owner = register_and_login(client)

    resp = client.get(
        "/api/v1/users/search?q=%20&limit=20",
        headers=auth_headers(owner["token"]),
    )

    assert resp.status_code == 200
    assert resp.json() == []
