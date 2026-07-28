"""Доменные исключения приложения.

Сервисы и эндпоинты бросают эти исключения вместо HTTPException (CLAUDE.md,
раздел 5.2). Преобразование в HTTP-ответ единого формата — в глобальном
обработчике, зарегистрированном в app/main.py. Коды ошибок соответствуют
реестру error.code в docs/API_SPEC.md, раздел 5.
"""

from typing import Any


class AppError(Exception):
    status_code: int = 500
    code: str = "INTERNAL_ERROR"

    def __init__(
        self,
        message: str,
        details: Any = None,
        headers: dict[str, str] | None = None,
    ):
        self.message = message
        self.details = details
        self.headers = headers
        super().__init__(message)


class ValidationError(AppError):
    status_code = 422
    code = "VALIDATION_ERROR"


class UnauthorizedError(AppError):
    status_code = 401
    code = "UNAUTHORIZED"


class ForbiddenError(AppError):
    status_code = 403
    code = "FORBIDDEN"


class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"


class EmailAlreadyExistsError(AppError):
    status_code = 409
    code = "EMAIL_ALREADY_EXISTS"


class InvalidCredentialsError(AppError):
    status_code = 401
    code = "INVALID_CREDENTIALS"


class LabelAlreadyExistsError(AppError):
    status_code = 409
    code = "LABEL_ALREADY_EXISTS"


class UnknownSortFieldError(AppError):
    status_code = 400
    code = "UNKNOWN_SORT_FIELD"


class ProjectMemberAlreadyExistsError(AppError):
    status_code = 409
    code = "MEMBER_ALREADY_EXISTS"


class LastProjectOwnerError(AppError):
    status_code = 409
    code = "LAST_PROJECT_OWNER"


class TooManyRequestsError(AppError):
    status_code = 429
    code = "TOO_MANY_REQUESTS"
