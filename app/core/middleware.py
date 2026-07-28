import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.context import correlation_id_ctx

logger = logging.getLogger("app.request")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Проставляет correlation ID и логирует каждый запрос одной строкой.

    correlationId читается из X-Request-ID или генерируется, возвращается
    клиенту в том же заголовке ответа (CLAUDE.md, раздел 8). userId
    берётся из request.state — его выставляет auth-зависимость (cur() в
    app/core/security.py), т.к. ContextVar, изменённый внутри
    call_next, не виден в этом коде после await (BaseHTTPMiddleware
    исполняет call_next в скопированном контексте).
    """

    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        correlation_id_ctx.set(correlation_id)

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        response.headers["X-Request-ID"] = correlation_id

        level = logging.INFO
        if response.status_code >= 500:
            level = logging.ERROR
        elif response.status_code >= 400:
            level = logging.WARNING

        logger.log(
            level,
            "request completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "statusCode": response.status_code,
                "durationMs": duration_ms,
                "clientIp": request.client.host if request.client else None,
                "userId": getattr(request.state, "user_id", None),
                "username": getattr(request.state, "username", None),
            },
        )

        return response
