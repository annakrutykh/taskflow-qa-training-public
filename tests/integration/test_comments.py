from tests.conftest import (
    add_member,
    auth_headers,
    create_project,
    create_task,
    register_and_login,
)


def _create_comment(client, token, task_id, text="A comment"):
    resp = client.post(
        f"/api/v1/tasks/{task_id}/comments",
        json={"text": text},
        headers=auth_headers(token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


class TestCreateAndListComments:
    def test_happy_path_has_location(self, client):
        owner = register_and_login(client)
        project_id = create_project(client, owner["token"])
        task = create_task(client, owner["token"], project_id)

        resp = client.post(
            f"/api/v1/tasks/{task['id']}/comments",
            json={"text": "hello"},
            headers=auth_headers(owner["token"]),
        )

        assert resp.status_code == 201
        assert "location" in resp.headers

    def test_viewer_can_comment(self, client):
        owner = register_and_login(client)
        viewer = register_and_login(client)
        project_id = create_project(client, owner["token"])
        add_member(client, owner["token"], project_id, viewer["user"]["id"], "VIEWER")
        task = create_task(client, owner["token"], project_id)

        resp = client.post(
            f"/api/v1/tasks/{task['id']}/comments",
            json={"text": "viewer comment"},
            headers=auth_headers(viewer["token"]),
        )

        assert resp.status_code == 201

    def test_stranger_cannot_comment(self, client):
        owner = register_and_login(client)
        stranger = register_and_login(client)
        project_id = create_project(client, owner["token"])
        task = create_task(client, owner["token"], project_id)

        resp = client.post(
            f"/api/v1/tasks/{task['id']}/comments",
            json={"text": "nope"},
            headers=auth_headers(stranger["token"]),
        )

        assert resp.status_code == 404


class TestUpdateComment:
    def test_author_can_edit(self, client):
        owner = register_and_login(client)
        project_id = create_project(client, owner["token"])
        task = create_task(client, owner["token"], project_id)
        comment = _create_comment(client, owner["token"], task["id"])

        resp = client.patch(
            f"/api/v1/tasks/{task['id']}/comments/{comment['id']}",
            json={"text": "edited"},
            headers=auth_headers(owner["token"]),
        )

        assert resp.status_code == 200
        assert resp.json()["text"] == "edited"

    def test_non_author_manager_cannot_edit(self, client):
        owner = register_and_login(client)
        manager = register_and_login(client)
        project_id = create_project(client, owner["token"])
        add_member(client, owner["token"], project_id, manager["user"]["id"], "MANAGER")
        task = create_task(client, owner["token"], project_id)
        comment = _create_comment(client, owner["token"], task["id"])

        resp = client.patch(
            f"/api/v1/tasks/{task['id']}/comments/{comment['id']}",
            json={"text": "hijacked"},
            headers=auth_headers(manager["token"]),
        )

        assert resp.status_code == 403


class TestDeleteComment:
    def test_manager_can_moderate_others_comment(self, client):
        owner = register_and_login(client)
        manager = register_and_login(client)
        project_id = create_project(client, owner["token"])
        add_member(client, owner["token"], project_id, manager["user"]["id"], "MANAGER")
        task = create_task(client, owner["token"], project_id)
        comment = _create_comment(client, owner["token"], task["id"])

        resp = client.delete(
            f"/api/v1/tasks/{task['id']}/comments/{comment['id']}",
            headers=auth_headers(manager["token"]),
        )

        assert resp.status_code == 204

    def test_viewer_cannot_delete_others_comment(self, client):
        owner = register_and_login(client)
        viewer = register_and_login(client)
        project_id = create_project(client, owner["token"])
        add_member(client, owner["token"], project_id, viewer["user"]["id"], "VIEWER")
        task = create_task(client, owner["token"], project_id)
        comment = _create_comment(client, owner["token"], task["id"])

        resp = client.delete(
            f"/api/v1/tasks/{task['id']}/comments/{comment['id']}",
            headers=auth_headers(viewer["token"]),
        )

        assert resp.status_code == 403


class TestTaskCommentsCount:
    def test_zero_for_new_task(self, client):
        owner = register_and_login(client)
        project_id = create_project(client, owner["token"])
        task = create_task(client, owner["token"], project_id)

        assert task["commentsCount"] == 0

    def test_reflects_created_and_deleted_comments(self, client):
        owner = register_and_login(client)
        project_id = create_project(client, owner["token"])
        task = create_task(client, owner["token"], project_id)

        first = _create_comment(client, owner["token"], task["id"])
        _create_comment(client, owner["token"], task["id"])

        get_resp = client.get(
            f"/api/v1/tasks/{task['id']}",
            headers=auth_headers(owner["token"]),
        )
        assert get_resp.json()["commentsCount"] == 2

        client.delete(
            f"/api/v1/tasks/{task['id']}/comments/{first['id']}",
            headers=auth_headers(owner["token"]),
        )

        get_resp = client.get(
            f"/api/v1/tasks/{task['id']}",
            headers=auth_headers(owner["token"]),
        )
        assert get_resp.json()["commentsCount"] == 1

    def test_reflected_in_list_tasks(self, client):
        owner = register_and_login(client)
        project_id = create_project(client, owner["token"])
        task = create_task(client, owner["token"], project_id)
        _create_comment(client, owner["token"], task["id"])

        resp = client.get(
            f"/api/v1/tasks?projectId={project_id}",
            headers=auth_headers(owner["token"]),
        )

        items = resp.json()["items"]
        assert next(t["commentsCount"] for t in items if t["id"] == task["id"]) == 1
