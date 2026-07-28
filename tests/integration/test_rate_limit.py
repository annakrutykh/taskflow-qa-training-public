"""Rate limiting на /auth/login и /auth/register (app/core/rate_limit.py).

Лимиты по умолчанию для тестового окружения выставлены очень высокими
(tests/conftest.py) — здесь они точечно занижаются через monkeypatch.setenv(),
чтобы не мешать остальным тестам, которым тоже нужен логин/регистрация.
"""

import pytest

from tests.conftest import auth_headers, register_and_login, unique_email


class TestLoginRateLimit:
    def test_returns_429_after_threshold(self, client, clean_redis, monkeypatch):
        monkeypatch.setenv("RATE_LIMIT_LOGIN_MAX_ATTEMPTS", "3")
        monkeypatch.setenv("RATE_LIMIT_LOGIN_WINDOW_SECONDS", "60")

        payload = {"email": "nobody@example.com", "password": "WrongPassword1!"}

        for _ in range(3):
            resp = client.post("/api/v1/auth/login", json=payload)
            assert resp.status_code == 401

        resp = client.post("/api/v1/auth/login", json=payload)

        assert resp.status_code == 429
        assert resp.json()["error"]["code"] == "TOO_MANY_REQUESTS"
        assert "Retry-After" in resp.headers

    def test_limit_is_per_client_not_per_account(
        self, client, clean_redis, monkeypatch
    ):
        """Лимит считается по IP клиента, а не по email — попытки логина под
        разными аккаунтами с одного клиента должны учитываться в одном счётчике."""
        monkeypatch.setenv("RATE_LIMIT_LOGIN_MAX_ATTEMPTS", "2")
        monkeypatch.setenv("RATE_LIMIT_LOGIN_WINDOW_SECONDS", "60")

        client.post(
            "/api/v1/auth/login",
            json={"email": "a@example.com", "password": "WrongPassword1!"},
        )
        client.post(
            "/api/v1/auth/login",
            json={"email": "b@example.com", "password": "WrongPassword1!"},
        )
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "c@example.com", "password": "WrongPassword1!"},
        )

        assert resp.status_code == 429


class TestRegisterRateLimit:
    def test_returns_429_after_threshold(self, client, clean_redis, monkeypatch):
        monkeypatch.setenv("RATE_LIMIT_REGISTER_MAX_ATTEMPTS", "2")
        monkeypatch.setenv("RATE_LIMIT_REGISTER_WINDOW_SECONDS", "60")

        def register():
            return client.post(
                "/api/v1/auth/register",
                json={
                    "email": unique_email(),
                    "password": "Password123!",
                    "firstName": "A",
                    "lastName": "B",
                },
            )

        assert register().status_code == 201
        assert register().status_code == 201

        resp = register()

        assert resp.status_code == 429
        assert resp.json()["error"]["code"] == "TOO_MANY_REQUESTS"


class TestLogout:
    @pytest.mark.smoke
    def test_logout_revokes_token(self, client):
        account = register_and_login(client)
        headers = auth_headers(account["token"])

        logout_resp = client.post("/api/v1/auth/logout", headers=headers)
        assert logout_resp.status_code == 204

        me_resp = client.get("/api/v1/users/me", headers=headers)
        assert me_resp.status_code == 401

    def test_logout_without_token_is_unauthorized(self, client):
        resp = client.post("/api/v1/auth/logout")

        assert resp.status_code == 401

    def test_other_tokens_remain_valid_after_logout(self, client):
        account_a = register_and_login(client)
        account_b = register_and_login(client)

        client.post("/api/v1/auth/logout", headers=auth_headers(account_a["token"]))

        resp = client.get("/api/v1/users/me", headers=auth_headers(account_b["token"]))

        assert resp.status_code == 200
