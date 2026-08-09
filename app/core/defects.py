"""Переключатель учебных сценариев поведения (CLAUDE.md, раздел 2).

Чёрный список: переменная окружения TRAINING_DEFECTS_DISABLED (через
запятую) перечисляет ID дефектов, которые нужно ВЫКЛЮЧИТЬ — для них
поведение соответствует docs/API_SPEC.md. Всё, что не перечислено,
ведёт себя как учебный дефект (включено).

По умолчанию (пусто) — не выключено ничего, активны все дефекты.

Специальное значение ALL выключает разом все дефекты, включая
появившиеся позже — без необходимости перечислять их поименно (нужно
трекам без охоты за багами, где список рос бы и требовал ручной
синхронизации при каждом новом D-XX).
"""

from app.core.config import settings

_DISABLE_ALL = "ALL"


class TrainingDefects:
    def __init__(self, raw: str):
        items = {item.strip().upper() for item in raw.split(",") if item.strip()}
        self._disable_all = _DISABLE_ALL in items
        self._disabled = items - {_DISABLE_ALL}

    def is_enabled(self, defect_id: str) -> bool:
        if self._disable_all:
            return False
        return defect_id.upper() not in self._disabled


defects = TrainingDefects(settings.training_defects_disabled)
