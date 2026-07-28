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
        owner = register_and_login(client)
        project_id = create_project(client, owner["token"])

        admin_list = client.get(
            "/api/v1/projects", headers=auth_headers(admin_token)
        ).json()

        assert project_id in [p["id"] for p in admin_list["items"]]

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
