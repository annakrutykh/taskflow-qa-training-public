import pytest

from tests.conftest import add_member, auth_headers, create_project, register_and_login


class TestCreateProject:
    @pytest.mark.smoke
    def test_happy_path_creates_owner_membership(self, client):
        account = register_and_login(client)

        resp = client.post(
            "/api/v1/projects",
            json={"name": "New Project", "description": "desc"},
            headers=auth_headers(account["token"]),
        )

        assert resp.status_code == 201
        assert "location" in resp.headers
        project = resp.json()
        assert project["name"] == "New Project"
        assert project["ownerId"] == account["user"]["id"]

        members = client.get(
            f"/api/v1/projects/{project['id']}/members",
            headers=auth_headers(account["token"]),
        ).json()
        assert members["total"] == 1
        assert members["items"][0]["userId"] == account["user"]["id"]
        assert members["items"][0]["role"] == "OWNER"

    def test_no_token_is_unauthorized(self, client):
        resp = client.post("/api/v1/projects", json={"name": "x"})

        assert resp.status_code == 401

    def test_blank_name_is_validation_error(self, client):
        account = register_and_login(client)

        resp = client.post(
            "/api/v1/projects",
            json={"name": ""},
            headers=auth_headers(account["token"]),
        )

        assert resp.status_code == 422


class TestListAndGetProject:
    def test_list_only_shows_member_projects(self, client):
        owner = register_and_login(client)
        stranger = register_and_login(client)
        project_id = create_project(client, owner["token"])

        owner_list = client.get(
            "/api/v1/projects", headers=auth_headers(owner["token"])
        ).json()
        stranger_list = client.get(
            "/api/v1/projects", headers=auth_headers(stranger["token"])
        ).json()

        assert project_id in [p["id"] for p in owner_list["items"]]
        assert project_id not in [p["id"] for p in stranger_list["items"]]

    def test_admin_sees_all_projects(self, client, admin_token):
        # GET /projects?limit=20&offset=0 (дефолт) сортирован по id ASC —
        # только что созданный проект имеет наибольший id и физически не
        # попадёт на первую страницу, если в БД уже накопилось 20+ проектов
        # (обычное дело в общей dev-БД после многих прогонов тестов). Прямой
        # GET /projects/{id} проверяет ровно то же самое (ADMIN обходит
        # проверку членства), не завися от объёма/сортировки списка.
        owner = register_and_login(client)
        project_id = create_project(client, owner["token"])

        resp = client.get(
            f"/api/v1/projects/{project_id}", headers=auth_headers(admin_token)
        )

        assert resp.status_code == 200
        assert resp.json()["id"] == project_id

    @pytest.mark.smoke
    def test_get_project_as_member_ok(self, client):
        owner = register_and_login(client)
        project_id = create_project(client, owner["token"])

        resp = client.get(
            f"/api/v1/projects/{project_id}", headers=auth_headers(owner["token"])
        )

        assert resp.status_code == 200

    def test_get_project_as_non_member_is_not_found(self, client):
        owner = register_and_login(client)
        stranger = register_and_login(client)
        project_id = create_project(client, owner["token"])

        resp = client.get(
            f"/api/v1/projects/{project_id}", headers=auth_headers(stranger["token"])
        )

        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "NOT_FOUND"


class TestUpdateProject:
    def test_owner_can_update(self, client):
        owner = register_and_login(client)
        project_id = create_project(client, owner["token"])

        resp = client.patch(
            f"/api/v1/projects/{project_id}",
            json={"status": "ARCHIVED"},
            headers=auth_headers(owner["token"]),
        )

        assert resp.status_code == 200
        assert resp.json()["status"] == "ARCHIVED"

    def test_viewer_cannot_update(self, client):
        owner = register_and_login(client)
        viewer = register_and_login(client)
        project_id = create_project(client, owner["token"])
        add_member(client, owner["token"], project_id, viewer["user"]["id"], "VIEWER")

        resp = client.patch(
            f"/api/v1/projects/{project_id}",
            json={"name": "hacked"},
            headers=auth_headers(viewer["token"]),
        )

        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "FORBIDDEN"

    def test_non_member_gets_not_found(self, client):
        owner = register_and_login(client)
        stranger = register_and_login(client)
        project_id = create_project(client, owner["token"])

        resp = client.patch(
            f"/api/v1/projects/{project_id}",
            json={"name": "hacked"},
            headers=auth_headers(stranger["token"]),
        )

        assert resp.status_code == 404

    def test_invalid_status_is_validation_error(self, client):
        owner = register_and_login(client)
        project_id = create_project(client, owner["token"])

        resp = client.patch(
            f"/api/v1/projects/{project_id}",
            json={"status": "NOT_A_STATUS"},
            headers=auth_headers(owner["token"]),
        )

        assert resp.status_code == 422


class TestDeleteProject:
    def test_owner_can_delete_and_it_cascades(self, client):
        owner = register_and_login(client)
        project_id = create_project(client, owner["token"])
        task_resp = client.post(
            "/api/v1/tasks",
            json={"projectId": project_id, "title": "will be cascaded"},
            headers=auth_headers(owner["token"]),
        )
        task_id = task_resp.json()["id"]

        delete_resp = client.delete(
            f"/api/v1/projects/{project_id}", headers=auth_headers(owner["token"])
        )
        assert delete_resp.status_code == 204

        assert (
            client.get(
                f"/api/v1/projects/{project_id}", headers=auth_headers(owner["token"])
            ).status_code
            == 404
        )
        assert (
            client.get(
                f"/api/v1/tasks/{task_id}", headers=auth_headers(owner["token"])
            ).status_code
            == 404
        )

    def test_manager_cannot_delete(self, client):
        owner = register_and_login(client)
        manager = register_and_login(client)
        project_id = create_project(client, owner["token"])
        add_member(client, owner["token"], project_id, manager["user"]["id"], "MANAGER")

        resp = client.delete(
            f"/api/v1/projects/{project_id}", headers=auth_headers(manager["token"])
        )

        assert resp.status_code == 403


class TestProjectMembers:
    def test_owner_can_add_member(self, client):
        owner = register_and_login(client)
        new_member = register_and_login(client)
        project_id = create_project(client, owner["token"])

        membership = add_member(
            client, owner["token"], project_id, new_member["user"]["id"], "MANAGER"
        )

        assert membership["userId"] == new_member["user"]["id"]
        assert membership["role"] == "MANAGER"

    def test_duplicate_member_is_conflict(self, client):
        owner = register_and_login(client)
        new_member = register_and_login(client)
        project_id = create_project(client, owner["token"])
        add_member(client, owner["token"], project_id, new_member["user"]["id"])

        resp = client.post(
            f"/api/v1/projects/{project_id}/members",
            json={"userId": new_member["user"]["id"], "role": "VIEWER"},
            headers=auth_headers(owner["token"]),
        )

        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "MEMBER_ALREADY_EXISTS"

    def test_manager_cannot_add_member(self, client):
        owner = register_and_login(client)
        manager = register_and_login(client)
        stranger = register_and_login(client)
        project_id = create_project(client, owner["token"])
        add_member(client, owner["token"], project_id, manager["user"]["id"], "MANAGER")

        resp = client.post(
            f"/api/v1/projects/{project_id}/members",
            json={"userId": stranger["user"]["id"], "role": "VIEWER"},
            headers=auth_headers(manager["token"]),
        )

        assert resp.status_code == 403

    def test_cannot_demote_last_owner(self, client):
        owner = register_and_login(client)
        project_id = create_project(client, owner["token"])

        resp = client.patch(
            f"/api/v1/projects/{project_id}/members/{owner['user']['id']}",
            json={"role": "MANAGER"},
            headers=auth_headers(owner["token"]),
        )

        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "LAST_PROJECT_OWNER"

    def test_cannot_remove_last_owner(self, client):
        owner = register_and_login(client)
        project_id = create_project(client, owner["token"])

        resp = client.delete(
            f"/api/v1/projects/{project_id}/members/{owner['user']['id']}",
            headers=auth_headers(owner["token"]),
        )

        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "LAST_PROJECT_OWNER"

    def test_adding_global_admin_forces_admin_project_role(self, client, admin_token):
        owner = register_and_login(client)
        project_id = create_project(client, owner["token"])
        future_admin = register_and_login(client)
        promote = client.patch(
            f"/api/v1/users/{future_admin['user']['id']}/role",
            json={"role": "ADMIN"},
            headers=auth_headers(admin_token),
        )
        assert promote.status_code == 200

        try:
            # Роль VIEWER передана явно, но должна быть проигнорирована —
            # глобальный ADMIN в project_members всегда получает роль ADMIN.
            membership = add_member(
                client, owner["token"], project_id, future_admin["user"]["id"], "VIEWER"
            )
            assert membership["role"] == "ADMIN"
        finally:
            client.patch(
                f"/api/v1/users/{future_admin['user']['id']}/role",
                json={"role": "USER"},
                headers=auth_headers(admin_token),
            )

    def test_cannot_assign_admin_project_role_to_regular_user(self, client):
        owner = register_and_login(client)
        regular = register_and_login(client)
        project_id = create_project(client, owner["token"])

        resp = client.post(
            f"/api/v1/projects/{project_id}/members",
            json={"userId": regular["user"]["id"], "role": "ADMIN"},
            headers=auth_headers(owner["token"]),
        )

        assert resp.status_code == 422

    def test_cannot_change_role_of_admin_project_member(self, client, admin_token):
        owner = register_and_login(client)
        project_id = create_project(client, owner["token"])
        future_admin = register_and_login(client)
        promote = client.patch(
            f"/api/v1/users/{future_admin['user']['id']}/role",
            json={"role": "ADMIN"},
            headers=auth_headers(admin_token),
        )
        assert promote.status_code == 200

        try:
            add_member(client, owner["token"], project_id, future_admin["user"]["id"])

            resp = client.patch(
                f"/api/v1/projects/{project_id}/members/{future_admin['user']['id']}",
                json={"role": "VIEWER"},
                headers=auth_headers(owner["token"]),
            )
            assert resp.status_code == 422
        finally:
            client.patch(
                f"/api/v1/users/{future_admin['user']['id']}/role",
                json={"role": "USER"},
                headers=auth_headers(admin_token),
            )

    def test_cannot_promote_regular_member_to_admin_project_role(self, client):
        owner = register_and_login(client)
        member = register_and_login(client)
        project_id = create_project(client, owner["token"])
        add_member(client, owner["token"], project_id, member["user"]["id"])

        resp = client.patch(
            f"/api/v1/projects/{project_id}/members/{member['user']['id']}",
            json={"role": "ADMIN"},
            headers=auth_headers(owner["token"]),
        )

        assert resp.status_code == 422

    def test_can_demote_owner_when_another_owner_exists(self, client):
        owner = register_and_login(client)
        second_owner = register_and_login(client)
        project_id = create_project(client, owner["token"])
        add_member(
            client, owner["token"], project_id, second_owner["user"]["id"], "OWNER"
        )

        resp = client.patch(
            f"/api/v1/projects/{project_id}/members/{owner['user']['id']}",
            json={"role": "MANAGER"},
            headers=auth_headers(owner["token"]),
        )

        assert resp.status_code == 200
