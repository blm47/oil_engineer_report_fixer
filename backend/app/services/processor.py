"""Применение правил из `channel_criteria.yaml` и подготовка предпросмотра корректировок.

ВАЖНО: корректировки НЕ применяются автоматически. Этот модуль всегда возвращает
пару (исходный канал, предложенная корректировка), а финальное решение — за инженером.

Сейчас — заглушка.
"""

from typing import Any


def build_preview(parsed_report: dict[str, Any], criteria: dict[str, Any]) -> dict[str, Any]:
    raise NotImplementedError("Correction preview will be implemented in a follow-up commit")
