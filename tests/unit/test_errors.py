"""Защита от расхождения между app/core/errors.py и реестром error.code в
docs/API_SPEC.md, раздел 5 — если кто-то поменяет status_code/code в одном
месте и забудет про другое, этот тест сломается."""

import pytest

from app.core import errors

pytestmark = pytest.mark.smoke  # без БД, доли секунды — всегда в smoke

# (класс, ожидаемый status_code, ожидаемый code) — должно совпадать с
# таблицей в docs/API_SPEC.md, раздел 5.
EXPECTED = [
    (errors.ValidationError, 422, "VALIDATION_ERROR"),
    (errors.UnauthorizedError, 401, "UNAUTHORIZED"),
    (errors.ForbiddenError, 403, "FORBIDDEN"),
    (errors.NotFoundError, 404, "NOT_FOUND"),
    (errors.EmailAlreadyExistsError, 409, "EMAIL_ALREADY_EXISTS"),
    (errors.InvalidCredentialsError, 401, "INVALID_CREDENTIALS"),
    (errors.LabelAlreadyExistsError, 409, "LABEL_ALREADY_EXISTS"),
    (errors.UnknownSortFieldError, 400, "UNKNOWN_SORT_FIELD"),
    (errors.ProjectMemberAlreadyExistsError, 409, "MEMBER_ALREADY_EXISTS"),
    (errors.LastProjectOwnerError, 409, "LAST_PROJECT_OWNER"),
]


@pytest.mark.parametrize(("error_cls", "status_code", "code"), EXPECTED)
def test_error_matches_registry(error_cls, status_code, code):
    assert error_cls.status_code == status_code
    assert error_cls.code == code


def test_error_carries_message_and_details():
    exc = errors.NotFoundError("Task not found", details={"taskId": 1})

    assert exc.message == "Task not found"
    assert exc.details == {"taskId": 1}
    assert str(exc) == "Task not found"
