"""Переключатель учебных сценариев поведения (CLAUDE.md, раздел 2).

Список включённых ID задаётся переменной окружения TRAINING_DEFECTS
(через запятую). По умолчанию (пусто) — все выключены, приложение ведёт
себя в соответствии с docs/API_SPEC.md.
"""

from app.core.config import settings


class TrainingDefects:
    def __init__(self, raw: str):
        self._enabled = {
            item.strip().upper() for item in raw.split(",") if item.strip()
        }

    def is_enabled(self, defect_id: str) -> bool:
        return defect_id.upper() in self._enabled


defects = TrainingDefects(settings.training_defects)
