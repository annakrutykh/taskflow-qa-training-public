"""Матрица прав app/permissions/projects.py — без БД (Session замокан),
как требует CLAUDE.md (раздел 10: "tests/unit/ — сервисы и матрица прав,
без БД")."""

import types
from unittest.mock import MagicMock

import pytest

from app.core.errors import ForbiddenError, NotFoundError
from app.models import ProjectRole
from app.permissions.projects import (
    TaskAccess,
    get_accessible_task,
    get_task_access,
    require_project_role,
    require_task_manage,
)

pytestmark = pytest.mark.smoke  # без БД, доли секунды — всегда в smoke


def make_user(user_id=1, role="USER"):
    return types.SimpleNamespace(id=user_id, role=role)


def make_project(project_id=1):
    return types.SimpleNamespace(id=project_id)


def make_membership(role):
    return types.SimpleNamespace(role=role)


def make_task(task_id=1, project_id=1, assignee_id=None):
    return types.SimpleNamespace(
        id=task_id, project_id=project_id, assignee_id=assignee_id, deleted_at=None
    )


class TestRequireProjectRole:
    def test_admin_bypasses_membership_check(self):
        db = MagicMock()
        admin = make_user(role="ADMIN")

        result = require_project_role(db, make_project(), admin, ProjectRole.OWNER)

        assert result is None
        db.get.assert_not_called()

    def test_non_member_gets_not_found_not_forbidden(self):
        db = MagicMock()
        db.get.return_value = None
        user = make_user(role="USER")

        with pytest.raises(NotFoundError):
            require_project_role(db, make_project(), user, ProjectRole.VIEWER)

    @pytest.mark.parametrize(
        ("member_role", "min_role"),
        [
            (ProjectRole.VIEWER, ProjectRole.MANAGER),
            (ProjectRole.VIEWER, ProjectRole.OWNER),
            (ProjectRole.MANAGER, ProjectRole.OWNER),
        ],
    )
    def test_member_with_insufficient_role_gets_forbidden(self, member_role, min_role):
        db = MagicMock()
        db.get.return_value = make_membership(member_role)
        user = make_user(role="USER")

        with pytest.raises(ForbiddenError):
            require_project_role(db, make_project(), user, min_role)

    @pytest.mark.parametrize(
        ("member_role", "min_role"),
        [
            (ProjectRole.VIEWER, ProjectRole.VIEWER),
            (ProjectRole.MANAGER, ProjectRole.VIEWER),
            (ProjectRole.MANAGER, ProjectRole.MANAGER),
            (ProjectRole.OWNER, ProjectRole.VIEWER),
            (ProjectRole.OWNER, ProjectRole.MANAGER),
            (ProjectRole.OWNER, ProjectRole.OWNER),
        ],
    )
    def test_member_with_sufficient_role_is_allowed(self, member_role, min_role):
        db = MagicMock()
        membership = make_membership(member_role)
        db.get.return_value = membership
        user = make_user(role="USER")

        result = require_project_role(db, make_project(), user, min_role)

        assert result is membership


class TestGetTaskAccess:
    def test_admin_gets_manager_level(self):
        db = MagicMock()
        admin = make_user(role="ADMIN")

        assert get_task_access(db, make_task(), admin) == TaskAccess.MANAGER
        db.get.assert_not_called()

    @pytest.mark.parametrize(
        ("member_role", "expected"),
        [
            (ProjectRole.OWNER, TaskAccess.MANAGER),
            (ProjectRole.MANAGER, TaskAccess.MANAGER),
            (ProjectRole.VIEWER, TaskAccess.VIEWER),
        ],
    )
    def test_project_member_access_level(self, member_role, expected):
        db = MagicMock()
        db.get.return_value = make_membership(member_role)
        user = make_user(user_id=2, role="USER")

        assert get_task_access(db, make_task(), user) == expected

    def test_viewer_member_who_is_also_assignee_gets_assignee_level(self):
        """VIEWER не должен быть строже, чем не-участник-исполнитель
        — иначе формальное членство в проекте отнимает право менять
        status, которое есть даже у постороннего исполнителя."""
        db = MagicMock()
        db.get.return_value = make_membership(ProjectRole.VIEWER)
        user = make_user(user_id=5, role="USER")
        task = make_task(assignee_id=5)

        assert get_task_access(db, task, user) == TaskAccess.ASSIGNEE

    def test_manager_member_who_is_also_assignee_stays_manager(self):
        db = MagicMock()
        db.get.return_value = make_membership(ProjectRole.MANAGER)
        user = make_user(user_id=5, role="USER")
        task = make_task(assignee_id=5)

        assert get_task_access(db, task, user) == TaskAccess.MANAGER

    def test_assignee_without_membership_gets_assignee_level(self):
        db = MagicMock()
        db.get.return_value = None
        user = make_user(user_id=5, role="USER")
        task = make_task(assignee_id=5)

        assert get_task_access(db, task, user) == TaskAccess.ASSIGNEE

    def test_stranger_gets_none(self):
        db = MagicMock()
        db.get.return_value = None
        user = make_user(user_id=99, role="USER")
        task = make_task(assignee_id=5)

        assert get_task_access(db, task, user) == TaskAccess.NONE


class TestGetAccessibleTask:
    def _mock_query(self, db, task):
        db.query.return_value.filter.return_value.first.return_value = task

    def test_missing_task_is_not_found(self):
        db = MagicMock()
        self._mock_query(db, None)
        user = make_user(role="USER")

        with pytest.raises(NotFoundError):
            get_accessible_task(db, 1, user)

    def test_task_with_no_access_is_not_found_not_forbidden(self):
        db = MagicMock()
        task = make_task(assignee_id=None)
        self._mock_query(db, task)
        db.get.return_value = None
        user = make_user(user_id=42, role="USER")

        with pytest.raises(NotFoundError):
            get_accessible_task(db, task.id, user)

    def test_accessible_task_is_returned(self):
        db = MagicMock()
        task = make_task(assignee_id=7)
        self._mock_query(db, task)
        db.get.return_value = None
        user = make_user(user_id=7, role="USER")

        assert get_accessible_task(db, task.id, user) is task


class TestRequireTaskManage:
    def test_viewer_cannot_manage(self):
        db = MagicMock()
        db.get.return_value = make_membership(ProjectRole.VIEWER)
        user = make_user(role="USER")

        with pytest.raises(ForbiddenError):
            require_task_manage(db, make_task(), user)

    def test_assignee_without_membership_cannot_manage(self):
        db = MagicMock()
        db.get.return_value = None
        user = make_user(user_id=3, role="USER")

        with pytest.raises(ForbiddenError):
            require_task_manage(db, make_task(assignee_id=3), user)

    def test_manager_can_manage(self):
        db = MagicMock()
        db.get.return_value = make_membership(ProjectRole.MANAGER)
        user = make_user(role="USER")

        require_task_manage(db, make_task(), user)  # не должно бросить исключение
