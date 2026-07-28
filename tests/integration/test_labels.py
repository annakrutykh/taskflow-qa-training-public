import uuid

from tests.conftest import (
    add_member,
    auth_headers,
    create_project,
    create_task,
    register_and_login,
)


def _label_name():
    return f"label-{uuid.uuid4().hex[:8]}"


class TestCreateLabel:
    def test_admin_can_create(self, client, admin_token):
        resp = client.post(
            "/api/v1/labels",
            json={"name": _label_name()},
            headers=auth_headers(admin_token),
        )

        assert resp.status_code == 201
        assert "location" in resp.headers

    def test_non_admin_cannot_create(self, client):
        account = register_and_login(client)

        resp = client.post(
            "/api/v1/labels",
            json={"name": _label_name()},
            headers=auth_headers(account["token"]),
        )

        assert resp.status_code == 403

    def test_duplicate_name_is_conflict(self, client, admin_token):
        name = _label_name()
        client.post(
            "/api/v1/labels", json={"name": name}, headers=auth_headers(admin_token)
        )

        resp = client.post(
            "/api/v1/labels", json={"name": name}, headers=auth_headers(admin_token)
        )

        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "LABEL_ALREADY_EXISTS"


class TestAttachDetachLabel:
    def test_manager_can_attach_and_detach(self, client, admin_token):
        owner = register_and_login(client)
        project_id = create_project(client, owner["token"])
        task = create_task(client, owner["token"], project_id)
        label = client.post(
            "/api/v1/labels",
            json={"name": _label_name()},
            headers=auth_headers(admin_token),
        ).json()

        attach_resp = client.post(
            f"/api/v1/tasks/{task['id']}/labels/{label['id']}",
            headers=auth_headers(owner["token"]),
        )
        assert attach_resp.status_code == 204

        task_after = client.get(
            f"/api/v1/tasks/{task['id']}", headers=auth_headers(owner["token"])
        ).json()
        assert label["id"] in [label_item["id"] for label_item in task_after["labels"]]

        detach_resp = client.delete(
            f"/api/v1/tasks/{task['id']}/labels/{label['id']}",
            headers=auth_headers(owner["token"]),
        )
        assert detach_resp.status_code == 204

        # повторный detach идемпотентен
        second_detach = client.delete(
            f"/api/v1/tasks/{task['id']}/labels/{label['id']}",
            headers=auth_headers(owner["token"]),
        )
        assert second_detach.status_code == 204

    def test_viewer_cannot_attach(self, client, admin_token):
        owner = register_and_login(client)
        viewer = register_and_login(client)
        project_id = create_project(client, owner["token"])
        add_member(client, owner["token"], project_id, viewer["user"]["id"], "VIEWER")
        task = create_task(client, owner["token"], project_id)
        label = client.post(
            "/api/v1/labels",
            json={"name": _label_name()},
            headers=auth_headers(admin_token),
        ).json()

        resp = client.post(
            f"/api/v1/tasks/{task['id']}/labels/{label['id']}",
            headers=auth_headers(viewer["token"]),
        )

        assert resp.status_code == 403


class TestDeleteLabel:
    def test_admin_can_delete(self, client, admin_token):
        label = client.post(
            "/api/v1/labels",
            json={"name": _label_name()},
            headers=auth_headers(admin_token),
        ).json()

        resp = client.delete(
            f"/api/v1/labels/{label['id']}", headers=auth_headers(admin_token)
        )

        assert resp.status_code == 204

    def test_non_admin_cannot_delete(self, client, admin_token):
        account = register_and_login(client)
        label = client.post(
            "/api/v1/labels",
            json={"name": _label_name()},
            headers=auth_headers(admin_token),
        ).json()

        resp = client.delete(
            f"/api/v1/labels/{label['id']}", headers=auth_headers(account["token"])
        )

        assert resp.status_code == 403
