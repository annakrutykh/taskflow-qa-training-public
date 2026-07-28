from tests.conftest import auth_headers, register_and_login


class TestAdminReset:
    def test_non_admin_cannot_reset(self, client):
        account = register_and_login(client)

        resp = client.post(
            "/api/v1/admin/reset", headers=auth_headers(account["token"])
        )

        assert resp.status_code == 403

    def test_admin_reset_restores_seed_state(self, client, admin_token):
        # намусорим данными
        register_and_login(client)

        resp = client.post("/api/v1/admin/reset", headers=auth_headers(admin_token))
        assert resp.status_code == 204

        # сид создаёт заново известного администратора
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "Admin123!"},
        )
        assert login_resp.status_code == 200

        fresh_admin_token = login_resp.json()["accessToken"]
        users = client.get(
            "/api/v1/users", headers=auth_headers(fresh_admin_token)
        ).json()
        assert users["total"] == 7  # см. app/core/seed.py
