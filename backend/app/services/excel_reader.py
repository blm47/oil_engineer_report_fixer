"""Чтение листов `Замес 1 Заказчику` и `Анализатор` из Excel-отчёта операции.

На данном этапе — только заглушка. Реальная реализация на pandas/openpyxl будет
добавлена в следующем коммите вместе с тестами на эталонных файлах.
"""

from pathlib import Path
from typing import Any

SHEET_MIX = "Замес 1 Заказчику"
SHEET_ANALYZER = "Анализатор"


def read_report(path: str | Path) -> dict[str, Any]:
    """Прочитать ключевые листы отчёта. Сейчас возвращает пустую структуру."""

    raise NotImplementedError("Excel parsing will be implemented in a follow-up commit")
