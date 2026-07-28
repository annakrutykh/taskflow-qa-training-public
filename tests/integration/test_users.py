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
