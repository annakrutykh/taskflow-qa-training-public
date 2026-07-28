"""Структурное логирование: один JSON-объект на строку (CLAUDE.md, раздел 8).

Тот же формат уходит в stdout (docker compose logs) и в Elasticsearch
(app/core/es_logging.py) — единый источник, два потребителя.

Никогда не логировать: пароли, JWT целиком (только первые 8 символов),
хеши паролей.
"""

import json
import logging
from datetime import UTC, datetime

from app.core.config import settings
from app.core.context import correlation_id_ctx

_EXTRA_FIELDS = (
    "method",
    "path",
    "statusCode",
    "durationMs",
    "clientIp",
    "userId",
    "username",
)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlationId": correlation_id_ctx.get(),
        }

        for field in _EXTRA_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False)


def configure_logging() -> None:
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers = [stream_handler]
    root.setLevel(logging.INFO)

    # шумные логгеры библиотек — не дублируем access-логи uvicorn,
    # у нас есть свой в middleware с нужным форматом
    logging.getLogger("uvicorn.access").disabled = True

    if settings.elasticsearch_enabled:
        # Собственные логи клиента ES (elastic_transport.transport,
        # elastic_transport.node_pool, ...) не должны улетать обратно в ES
        # тем же обработчиком — иначе каждый bulk-запрос порождает новую
        # запись лога о самом себе (шум + лишняя нагрузка). .disabled не
        # наследуется дочерними логгерами — гасим через уровень: дочерние
        # логгеры без собственного level наследуют его от родителя.
        logging.getLogger("elastic_transport").setLevel(logging.CRITICAL)
        logging.getLogger("elasticsearch").setLevel(logging.CRITICAL)

        # Отложенный импорт: es_logging.py импортирует JsonFormatter отсюда же,
        # импорт на уровне модуля дал бы циклическую зависимость.
        from app.core.es_logging import ElasticsearchHandler

        root.addHandler(ElasticsearchHandler())
