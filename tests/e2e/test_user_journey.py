"""Полный пользовательский сценарий (CLAUDE.md, раздел 10:
"tests/e2e/ — полные пользовательские сценарии"), одним связным потоком,
а не изолированными проверками отдельных ручек."""

from tests.conftest import auth_headers, register_and_login


def test_full_project_lifecycle(client, admin_token):
    # 1. Менеджер регистрируется, логинится, создаёт проект (становится OWNER).
    manager = register_and_login(client)
    project = client.post(
        "/api/v1/projects",
        json={"name": "E2E Project", "description": "Полный сценарий"},
        headers=auth_headers(manager["token"]),
    ).json()

    # 2. Добавляет исполнителя как VIEWER (доступ к остальным задачам проекта,
    # не только к своей).
    assignee = register_and_login(client)
    client.post(
        f"/api/v1/projects/{project['id']}/members",
        json={"userId": assignee["user"]["id"], "role": "VIEWER"},
        headers=auth_headers(manager["token"]),
    )

    # 3. Создаёт задачу и назначает исполнителя.
    task = client.post(
        "/api/v1/tasks",
        json={
            "projectId": project["id"],
            "title": "Реализовать фичу",
            "priority": "HIGH",
            "assigneeId": assignee["user"]["id"],
        },
        headers=auth_headers(manager["token"]),
    ).json()
    assert task["status"] == "TODO"
    assert task["labels"] == []

    # 4. Админ создаёт метку и менеджер привязывает её к задаче.
    label = client.post(
        "/api/v1/labels",
        json={"name": "e2e-feature"},
        headers=auth_headers(admin_token),
    ).json()
    attach = client.post(
        f"/api/v1/tasks/{task['id']}/labels/{label['id']}",
        headers=auth_headers(manager["token"]),
    )
    assert attach.status_code == 204

    # 5. Исполнитель видит задачу (он VIEWER проекта), берёт в работу.
    in_progress = client.patch(
        f"/api/v1/tasks/{task['id']}",
        json={"status": "IN_PROGRESS"},
        headers=auth_headers(assignee["token"]),
    )
    assert in_progress.status_code == 200
    assert in_progress.json()["status"] == "IN_PROGRESS"

    # 6. Исполнитель оставляет комментарий о прогрессе.
    comment = client.post(
        f"/api/v1/tasks/{task['id']}/comments",
        json={"text": "Начал работу, готово наполовину"},
        headers=auth_headers(assignee["token"]),
    )
    assert comment.status_code == 201

    # 7. Исполнитель не может сам менять другие поля задачи — только статус.
    forbidden = client.patch(
        f"/api/v1/tasks/{task['id']}",
        json={"priority": "LOW"},
        headers=auth_headers(assignee["token"]),
    )
    assert forbidden.status_code == 403

    # 8. Менеджер закрывает задачу.
    done = client.patch(
        f"/api/v1/tasks/{task['id']}",
        json={"status": "DONE"},
        headers=auth_headers(manager["token"]),
    )
    assert done.status_code == 200
    assert done.json()["status"] == "DONE"

    # 9. Финальная задача видна в списке с меткой и корректной пагинацией.
    listing = client.get(
        f"/api/v1/tasks?projectId={project['id']}",
        headers=auth_headers(manager["token"]),
    ).json()
    assert listing["total"] == 1
    assert listing["hasNext"] is False
    final_task = listing["items"][0]
    assert final_task["id"] == task["id"]
    assert label["id"] in [item["id"] for item in final_task["labels"]]

    comments = client.get(
        f"/api/v1/tasks/{task['id']}/comments",
        headers=auth_headers(manager["token"]),
    ).json()
    assert comments["total"] == 1

    # 10. Посторонний не видит ни проект, ни задачу.
    stranger = register_and_login(client)
    assert (
        client.get(
            f"/api/v1/projects/{project['id']}", headers=auth_headers(stranger["token"])
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/api/v1/tasks/{task['id']}", headers=auth_headers(stranger["token"])
        ).status_code
        == 404
    )

    # 11. Менеджер удаляет проект — каскадно исчезает и задача.
    delete_resp = client.delete(
        f"/api/v1/projects/{project['id']}", headers=auth_headers(manager["token"])
    )
    assert delete_resp.status_code == 204
    assert (
        client.get(
            f"/api/v1/tasks/{task['id']}", headers=auth_headers(manager["token"])
        ).status_code
        == 404
    )
