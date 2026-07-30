import pytest

from tests.conftest import (
    add_member,
    auth_headers,
    create_project,
    create_task,
    register_and_login,
)


class TestCreateTask:
    @pytest.mark.smoke
    def test_manager_can_create(self, client):
        owner = register_and_login(client)
        project_id = create_project(client, owner["token"])

        resp = client.post(
            "/api/v1/tasks",
            json={"projectId": project_id, "title": "Do the thing", "priority": "HIGH"},
            headers=auth_headers(owner["token"]),
        )

        assert resp.status_code == 201
        assert "location" in resp.headers
        body = resp.json()
        assert body["title"] == "Do the thing"
        assert body["status"] == "TODO"
        assert body["priority"] == "HIGH"
        assert body["labels"] == []
        assert body["assigneeFirstName"] is None
        assert body["assigneeLastName"] is None

    def test_assignee_name_is_included(self, client):
        owner = register_and_login(client)
        assignee = register_and_login(client)
        project_id = create_project(client, owner["token"])

        resp = client.post(
            "/api/v1/tasks",
            json={
                "projectId": project_id,
                "title": "Do the thing",
                "assigneeId": assignee["user"]["id"],
            },
            headers=auth_headers(owner["token"]),
        )

        assert resp.status_code == 201
        body = resp.json()
        assert body["assigneeFirstName"] == assignee["user"]["firstName"]
        assert body["assigneeLastName"] == assignee["user"]["lastName"]

    def test_viewer_cannot_create(self, client):
        owner = register_and_login(client)
        viewer = register_and_login(client)
        project_id = create_project(client, owner["token"])
        add_member(client, owner["token"], project_id, viewer["user"]["id"], "VIEWER")

        resp = client.post(
            "/api/v1/tasks",
            json={"projectId": project_id, "title": "nope"},
            headers=auth_headers(viewer["token"]),
        )

        assert resp.status_code == 403

    def test_non_member_gets_project_not_found(self, client):
        owner = register_and_login(client)
        stranger = register_and_login(client)
        project_id = create_project(client, owner["token"])

        resp = client.post(
            "/api/v1/tasks",
            json={"projectId": project_id, "title": "nope"},
            headers=auth_headers(stranger["token"]),
        )

        assert resp.status_code == 404

    def test_nonexistent_assignee_is_not_found(self, client):
        owner = register_and_login(client)
        project_id = create_project(client, owner["token"])

        resp = client.post(
            "/api/v1/tasks",
            json={"projectId": project_id, "title": "x", "assigneeId": 999999999},
            headers=auth_headers(owner["token"]),
        )

        assert resp.status_code == 404

    def test_blank_title_is_validation_error(self, client):
        owner = register_and_login(client)
        project_id = create_project(client, owner["token"])

        resp = client.post(
            "/api/v1/tasks",
            json={"projectId": project_id, "title": ""},
            headers=auth_headers(owner["token"]),
        )

        assert resp.status_code == 422


class TestGetTask:
    @pytest.mark.smoke
    def test_viewer_can_view(self, client):
        owner = register_and_login(client)
        viewer = register_and_login(client)
        project_id = create_project(client, owner["token"])
        add_member(client, owner["token"], project_id, viewer["user"]["id"], "VIEWER")
        task = create_task(client, owner["token"], project_id)

        resp = client.get(
            f"/api/v1/tasks/{task['id']}", headers=auth_headers(viewer["token"])
        )

        assert resp.status_code == 200

    def test_assignee_without_membership_can_view(self, client):
        owner = register_and_login(client)
        assignee = register_and_login(client)
        project_id = create_project(client, owner["token"])
        task = create_task(
            client,
            owner["token"],
            project_id,
            assigneeId=assignee["user"]["id"],
        )

        resp = client.get(
            f"/api/v1/tasks/{task['id']}", headers=auth_headers(assignee["token"])
        )

        assert resp.status_code == 200

    def test_stranger_gets_not_found(self, client):
        owner = register_and_login(client)
        stranger = register_and_login(client)
        project_id = create_project(client, owner["token"])
        task = create_task(client, owner["token"], project_id)

        resp = client.get(
            f"/api/v1/tasks/{task['id']}", headers=auth_headers(stranger["token"])
        )

        assert resp.status_code == 404


class TestUpdateTask:
    def test_manager_can_change_any_field(self, client):
        owner = register_and_login(client)
        project_id = create_project(client, owner["token"])
        task = create_task(client, owner["token"], project_id)

        resp = client.patch(
            f"/api/v1/tasks/{task['id']}",
            json={"title": "renamed", "priority": "LOW"},
            headers=auth_headers(owner["token"]),
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["title"] == "renamed"
        assert body["priority"] == "LOW"

    def test_assignee_without_membership_can_only_change_status(self, client):
        owner = register_and_login(client)
        assignee = register_and_login(client)
        project_id = create_project(client, owner["token"])
        task = create_task(
            client, owner["token"], project_id, assigneeId=assignee["user"]["id"]
        )

        status_resp = client.patch(
            f"/api/v1/tasks/{task['id']}",
            json={"status": "IN_PROGRESS"},
            headers=auth_headers(assignee["token"]),
        )
        assert status_resp.status_code == 200
        assert status_resp.json()["status"] == "IN_PROGRESS"

        title_resp = client.patch(
            f"/api/v1/tasks/{task['id']}",
            json={"title": "hacked"},
            headers=auth_headers(assignee["token"]),
        )
        assert title_resp.status_code == 403
        assert title_resp.json()["error"]["code"] == "FORBIDDEN"

    def test_viewer_cannot_change_anything(self, client):
        owner = register_and_login(client)
        viewer = register_and_login(client)
        project_id = create_project(client, owner["token"])
        add_member(client, owner["token"], project_id, viewer["user"]["id"], "VIEWER")
        task = create_task(client, owner["token"], project_id)

        resp = client.patch(
            f"/api/v1/tasks/{task['id']}",
            json={"status": "DONE"},
            headers=auth_headers(viewer["token"]),
        )

        assert resp.status_code == 403

    def test_manager_can_reassign(self, client):
        owner = register_and_login(client)
        first_assignee = register_and_login(client)
        second_assignee = register_and_login(client)
        project_id = create_project(client, owner["token"])
        task = create_task(
            client,
            owner["token"],
            project_id,
            assigneeId=first_assignee["user"]["id"],
        )

        resp = client.patch(
            f"/api/v1/tasks/{task['id']}",
            json={"assigneeId": second_assignee["user"]["id"]},
            headers=auth_headers(owner["token"]),
        )

        assert resp.status_code == 200
        assert resp.json()["assigneeId"] == second_assignee["user"]["id"]

    def test_manager_can_unassign(self, client):
        owner = register_and_login(client)
        assignee = register_and_login(client)
        project_id = create_project(client, owner["token"])
        task = create_task(
            client, owner["token"], project_id, assigneeId=assignee["user"]["id"]
        )

        resp = client.patch(
            f"/api/v1/tasks/{task['id']}",
            json={"assigneeId": None},
            headers=auth_headers(owner["token"]),
        )

        assert resp.status_code == 200
        assert resp.json()["assigneeId"] is None

    def test_reassign_to_nonexistent_user_is_not_found(self, client):
        owner = register_and_login(client)
        project_id = create_project(client, owner["token"])
        task = create_task(client, owner["token"], project_id)

        resp = client.patch(
            f"/api/v1/tasks/{task['id']}",
            json={"assigneeId": 999999999},
            headers=auth_headers(owner["token"]),
        )

        assert resp.status_code == 404

    def test_assignee_without_membership_cannot_reassign(self, client):
        owner = register_and_login(client)
        assignee = register_and_login(client)
        other = register_and_login(client)
        project_id = create_project(client, owner["token"])
        task = create_task(
            client, owner["token"], project_id, assigneeId=assignee["user"]["id"]
        )

        resp = client.patch(
            f"/api/v1/tasks/{task['id']}",
            json={"assigneeId": other["user"]["id"]},
            headers=auth_headers(assignee["token"]),
        )

        assert resp.status_code == 403


class TestDeleteTask:
    def test_manager_can_delete(self, client):
        owner = register_and_login(client)
        project_id = create_project(client, owner["token"])
        task = create_task(client, owner["token"], project_id)

        resp = client.delete(
            f"/api/v1/tasks/{task['id']}", headers=auth_headers(owner["token"])
        )

        assert resp.status_code == 204

    def test_assignee_without_membership_cannot_delete(self, client):
        owner = register_and_login(client)
        assignee = register_and_login(client)
        project_id = create_project(client, owner["token"])
        task = create_task(
            client, owner["token"], project_id, assigneeId=assignee["user"]["id"]
        )

        resp = client.delete(
            f"/api/v1/tasks/{task['id']}", headers=auth_headers(assignee["token"])
        )

        assert resp.status_code == 403


class TestListTasks:
    def test_unknown_sort_field_is_400(self, client):
        owner = register_and_login(client)

        resp = client.get(
            "/api/v1/tasks?sort=bogus", headers=auth_headers(owner["token"])
        )

        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "UNKNOWN_SORT_FIELD"

    def test_sort_by_priority_is_logical_order_by_default(self, client):
        owner = register_and_login(client)
        project_id = create_project(client, owner["token"])
        create_task(client, owner["token"], project_id, title="a", priority="HIGH")
        create_task(client, owner["token"], project_id, title="b", priority="LOW")
        create_task(client, owner["token"], project_id, title="c", priority="MEDIUM")

        resp = client.get(
            f"/api/v1/tasks?projectId={project_id}&sort=priority&order=asc",
            headers=auth_headers(owner["token"]),
        )

        assert resp.status_code == 200
        priorities = [t["priority"] for t in resp.json()["items"]]
        assert priorities == ["LOW", "MEDIUM", "HIGH"]

    def test_list_excludes_other_users_tasks(self, client):
        owner = register_and_login(client)
        stranger = register_and_login(client)
        project_id = create_project(client, owner["token"])
        task = create_task(client, owner["token"], project_id)

        stranger_tasks = client.get(
            "/api/v1/tasks", headers=auth_headers(stranger["token"])
        ).json()

        assert task["id"] not in [t["id"] for t in stranger_tasks["items"]]
