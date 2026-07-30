import uuid

from tests.conftest import auth_headers, create_project, register_and_login


class TestMe:
    def test_get_me(self, client):
        account = register_and_login(client)

        resp = client.get("/api/v1/users/me", headers=auth_headers(account["token"]))

        assert resp.status_code == 200
        assert resp.json()["email"] == account["email"]

    def test_patch_me(self, client):
        account = register_and_login(client)

        resp = client.patch(
            "/api/v1/users/me",
            json={"firstName": "Changed"},
            headers=auth_headers(account["token"]),
        )

        assert resp.status_code == 200
        assert resp.json()["firstName"] == "Changed"


class TestAdminOnlyUserManagement:
    def test_non_admin_cannot_list_users(self, client):
        account = register_and_login(client)

        resp = client.get("/api/v1/users", headers=auth_headers(account["token"]))

        assert resp.status_code == 403

    def test_admin_can_list_users(self, client, admin_token):
        resp = client.get("/api/v1/users", headers=auth_headers(admin_token))

        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_admin_can_get_user_by_id(self, client, admin_token):
        account = register_and_login(client)

        resp = client.get(
            f"/api/v1/users/{account['user']['id']}",
            headers=auth_headers(admin_token),
        )

        assert resp.status_code == 200
        assert resp.json()["email"] == account["email"]

    def test_admin_get_unknown_user_is_not_found(self, client, admin_token):
        resp = client.get("/api/v1/users/999999999", headers=auth_headers(admin_token))

        assert resp.status_code == 404

    def test_admin_can_change_role(self, client, admin_token):
        account = register_and_login(client)

        resp = client.patch(
            f"/api/v1/users/{account['user']['id']}/role",
            json={"role": "ADMIN"},
            headers=auth_headers(admin_token),
        )

        assert resp.status_code == 200
        assert resp.json()["role"] == "ADMIN"

    def test_non_admin_cannot_change_role(self, client):
        account = register_and_login(client)
        other = register_and_login(client)

        resp = client.patch(
            f"/api/v1/users/{other['user']['id']}/role",
            json={"role": "ADMIN"},
            headers=auth_headers(account["token"]),
        )

        assert resp.status_code == 403

    def test_admin_can_deactivate_user(self, client, admin_token):
        account = register_and_login(client)

        resp = client.patch(
            f"/api/v1/users/{account['user']['id']}/status",
            json={"isActive": False},
            headers=auth_headers(admin_token),
        )

        assert resp.status_code == 200
        assert resp.json()["isActive"] is False

        login_resp = client.post(
            "/api/v1/auth/login",
            json={"email": account["email"], "password": account["password"]},
        )
        assert login_resp.status_code == 401

    def test_admin_can_delete_user(self, client, admin_token):
        account = register_and_login(client)

        resp = client.delete(
            f"/api/v1/users/{account['user']['id']}",
            headers=auth_headers(admin_token),
        )

        assert resp.status_code == 204

    def test_deleting_sole_project_owner_is_conflict(self, client, admin_token):
        account = register_and_login(client)
        create_project(client, account["token"])

        resp = client.delete(
            f"/api/v1/users/{account['user']['id']}",
            headers=auth_headers(admin_token),
        )

        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "LAST_PROJECT_OWNER"


class TestUserSearch:
    """GET /users/search — доступно любому авторизованному (в отличие от
    GET /users), нужно для приглашения в проект по имени без ADMIN-доступа."""

    def _register(self, client, first_name: str, last_name: str) -> dict:
        email = f"search-{uuid.uuid4().hex[:12]}@example.com"
        password = "Password123!"

        resp = client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": password,
                "firstName": first_name,
                "lastName": last_name,
            },
        )
        assert resp.status_code == 201, resp.text

        login_resp = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert login_resp.status_code == 200, login_resp.text

        return {
            "user": resp.json(),
            "token": login_resp.json()["accessToken"],
            "email": email,
        }

    def test_non_admin_can_search_by_first_name(self, client):
        searcher = register_and_login(client)
        tag = uuid.uuid4().hex[:8]
        target = self._register(client, f"Zeliboba{tag}", "Testerov")

        resp = client.get(
            f"/api/v1/users/search?q=Zeliboba{tag}",
            headers=auth_headers(searcher["token"]),
        )

        assert resp.status_code == 200
        emails = {u["email"] for u in resp.json()}
        assert target["email"] in emails
        assert "role" not in resp.json()[0]
        assert "isActive" not in resp.json()[0]

    def test_search_by_email_substring(self, client):
        searcher = register_and_login(client)
        target = self._register(client, "Ann", "Search")

        resp = client.get(
            f"/api/v1/users/search?q={target['email'][:10]}",
            headers=auth_headers(searcher["token"]),
        )

        assert resp.status_code == 200
        assert any(u["email"] == target["email"] for u in resp.json())

    def test_search_requires_nonempty_query(self, client):
        searcher = register_and_login(client)

        resp = client.get(
            "/api/v1/users/search?q=", headers=auth_headers(searcher["token"])
        )

        assert resp.status_code == 422

    def test_search_requires_auth(self, client):
        resp = client.get("/api/v1/users/search?q=test")

        assert resp.status_code == 401

    def test_search_no_match_returns_empty_list(self, client):
        searcher = register_and_login(client)

        resp = client.get(
            f"/api/v1/users/search?q=nobody-{uuid.uuid4().hex}",
            headers=auth_headers(searcher["token"]),
        )

        assert resp.status_code == 200
        assert resp.json() == []
