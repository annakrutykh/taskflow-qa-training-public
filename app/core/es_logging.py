"""Отправка структурных логов в Elasticsearch (CLAUDE.md, раздел 8).

Дизайн: logging.Handler кладёт запись в очередь в памяти (неблокирующе —
put_nowait) и сразу возвращает управление обработчику запроса; отдельный
фоновый поток вычитывает очередь и пишет документы в ES через bulk API.
Так задержка/недоступность Elasticsearch не влияет на время ответа API.

Fail-open: любая ошибка ES (недоступен, не готов, переполнен) — только
warning в stderr, ни один запрос не должен упасть из-за логирования.
Очередь ограничена (_QUEUE_MAXSIZE) — если консьюмер не успевает (или ES
лежит долго), новые записи логов отбрасываются, а не копятся неограниченно
в памяти процесса.

Индекс — новый на каждый день (`taskflow-logs-YYYY.MM.DD`), поле `@timestamp`
для нормальной работы Kibana Discover/Data View "по времени".
"""

import atexit
import json
import logging
import queue
import threading
from datetime import UTC, datetime

from elasticsearch import Elasticsearch

from app.core.config import settings
from app.core.logging import JsonFormatter

_QUEUE_MAXSIZE = 10_000
_FLUSH_BATCH_SIZE = 200
_FLUSH_INTERVAL_SECONDS = 1.0

_fallback_logger = logging.getLogger("app.es_logging")


class ElasticsearchHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self._formatter = JsonFormatter()
        self._queue: queue.Queue = queue.Queue(maxsize=_QUEUE_MAXSIZE)
        self._client = Elasticsearch(settings.elasticsearch_url, request_timeout=2)
        self._stop_event = threading.Event()
        self._thread = threading.Thread(
            target=self._consume_loop, name="es-log-shipper", daemon=True
        )
        self._thread.start()
        atexit.register(self._stop)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            document = json.loads(self._formatter.format(record))
            document["@timestamp"] = datetime.now(UTC).isoformat()
        except Exception:  # noqa: BLE001 — логирование не должно падать никогда
            return

        try:
            self._queue.put_nowait(document)
        except queue.Full:
            pass  # консьюмер не успевает — теряем запись лога, не блокируем запрос

    def _consume_loop(self) -> None:
        batch = []

        while not self._stop_event.is_set():
            try:
                document = self._queue.get(timeout=_FLUSH_INTERVAL_SECONDS)
                batch.append(document)
                if len(batch) >= _FLUSH_BATCH_SIZE:
                    self._flush(batch)
                    batch = []
            except queue.Empty:
                if batch:
                    self._flush(batch)
                    batch = []

    def _flush(self, batch: list[dict]) -> None:
        index_name = f"taskflow-logs-{datetime.now(UTC):%Y.%m.%d}"

        try:
            operations = []
            for document in batch:
                operations.append({"index": {"_index": index_name}})
                operations.append(document)
            self._client.bulk(operations=operations)
        except Exception as exc:  # noqa: BLE001 — ES может отказывать по-разному
            _fallback_logger.warning("Elasticsearch недоступен, логи потеряны: %s", exc)

    def _stop(self) -> None:
        self._stop_event.set()
        self._thread.join(timeout=2)
