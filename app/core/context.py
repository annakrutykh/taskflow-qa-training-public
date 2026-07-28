"""ContextVar-хранилища для сквозных данных запроса (correlation ID, пользователь).

Используются логированием и глобальным обработчиком ошибок, чтобы не
прокидывать эти значения явно через каждый вызов.
"""

from contextvars import ContextVar

correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="-")
