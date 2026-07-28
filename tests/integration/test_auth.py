import pytest

from tests.conftest import auth_headers, register_and_login, unique_email


class TestRegister:
    @pytest.mark.smoke
    def test_happy_path_returns_camel_case_and_location(self, client):
        email = unique_email()

        resp = client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "Password123!",
                "firstName": "Ivan",
                "lastName": "Ivanov",
            },
        )

        assert resp.status_code == 201
        assert "location" in resp.headers
        body = resp.json()
        assert body["email"] == email
        assert body["firstName"] == "Ivan"
        assert body["lastName"] == "Ivanov"
        assert body["role"] == "USER"
        assert body["isActive"] is True

    def test_duplicate_email_is_conflict(self, client):
        email = unique_email()
        payload = {
            "email": email,
            "password": "Password123!",
            "firstName": "A",
            "lastName": "B",
        }

        first = client.post("/api/v1/auth/register", json=payload)
        assert first.status_code == 201

        second = client.post("/api/v1/auth/register", json=payload)
        assert second.status_code == 409
        assert second.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"

    def test_short_password_is_validation_error(self, client):
        resp = client.post(
            "/api/v1/auth/register",
            json={
                "email": unique_email(),
                "password": "short",
                "firstName": "A",
                "lastName": "B",
            },
        )

        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


class TestLogin:
    @pytest.mark.smoke
    def test_happy_path(self, client):
        account = register_and_login(client)

        resp = client.post(
            "/api/v1/auth/login",
            json={"email": account["email"], "password": account["password"]},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["tokenType"] == "bearer"
        assert isinstance(body["accessToken"], str) and body["accessToken"]

    def test_wrong_password_is_invalid_credentials(self, client):
        account = register_and_login(client)

        resp = client.post(
            "/api/v1/auth/login",
            json={"email": account["email"], "password": "WrongPassword1!"},
        )

        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"

    def test_unknown_email_is_invalid_credentials_not_404(self, client):
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": unique_email(), "password": "Whatever123!"},
        )

        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"

    def test_deactivated_user_cannot_login(self, client):
        # olga@example.com — деактивированный пользователь из seed.py.
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "olga@example.com", "password": "User123!"},
        )

        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"

    def test_missing_field_is_validation_error(self, client):
        resp = client.post("/api/v1/auth/login", json={"email": unique_email()})

        assert resp.status_code == 422


class TestTokenValidation:
    @pytest.mark.smoke
    def test_no_token_is_unauthorized(self, client):
        resp = client.get("/api/v1/users/me")

        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "UNAUTHORIZED"

    def test_invalid_token_is_unauthorized(self, client):
        resp = client.get("/api/v1/users/me", headers=auth_headers("not-a-real-token"))

        assert resp.status_code == 401

    @pytest.mark.smoke
    def test_valid_token_is_accepted(self, client):
        account = register_and_login(client)

        resp = client.get("/api/v1/users/me", headers=auth_headers(account["token"]))

        assert resp.status_code == 200
        assert resp.json()["email"] == account["email"]
