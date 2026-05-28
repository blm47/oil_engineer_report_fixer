from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field

import pandas as pd

logger = logging.getLogger(__name__)

SHEET_CUSTOMER = "Замещение (Заказчику)"
SHEET_ANALYZER = "Замещение (Анализатор)"
TIME_ALIASES = ["время", "time", "hh:mm:ss", "hhmmss"]


@dataclass
class ParsedSeries:
    channel_num: int
    name: str
    unit: str
    x: list[float] = field(default_factory=list)
    y: list[float] = field(default_factory=list)
    y_corrected: list[float] = field(default_factory=list)
    correction_applied: bool = False


@dataclass
class ParsedWorkbook:
    customer_sheet: str | None
    analyzer_sheet: str | None
    charts: list[ParsedSeries]


# ---------------------------------------------------------------------------
# Утилиты
# ---------------------------------------------------------------------------
def _safe_float_list(values: list) -> list[float]:
    result = []
    for v in values:
        try:
            f = float(v)
            result.append(round(f, 4) if math.isfinite(f) else 0.0)
        except (TypeError, ValueError):
            result.append(0.0)
    return result


def _coerce_numeric(series: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(series):
        return series.astype(float)
    cleaned = (
        series.astype(str)
        .str.replace(",", ".", regex=False)
        .str.strip()
        .replace({"nan": None, "None": None, "": None})
    )
    return pd.to_numeric(cleaned, errors="coerce")


def _normalize(s) -> str:
    """Нормализация для СРАВНЕНИЯ — нижний регистр."""
    return str(s).strip().replace("\xa0", " ").replace("  ", " ").lower()


def _clean(s) -> str:
    """Очистка для ХРАНЕНИЯ — сохраняет регистр и единицы."""
    return str(s).strip().replace("\xa0", " ").replace("  ", " ")


def _find_sheet_name(excel_file: pd.ExcelFile, target: str) -> str | None:
    target_norm = _normalize(target)
    for sheet in excel_file.sheet_names:
        if _normalize(sheet) == target_norm:
            return sheet
    for sheet in excel_file.sheet_names:
        if target_norm in _normalize(sheet):
            return sheet
    return None


def _parse_time_to_minutes(series: pd.Series) -> list[float]:
    numeric = _coerce_numeric(series).bfill().ffill().fillna(0.0)
    values = _safe_float_list(numeric.tolist())
    if not values:
        return []
    max_val = max(abs(v) for v in values)
    if max_val > 1000:
        result = []
        for v in values:
            iv = int(v)
            hh = iv // 10000
            mm = (iv % 10000) // 100
            ss = iv % 100
            result.append(hh * 60.0 + mm + ss / 60.0)
        start = result[0]
        return [round(t - start, 4) for t in result]
    else:
        start = values[0]
        return [round(v - start, 4) for v in values]


# ---------------------------------------------------------------------------
# Критерии
# ---------------------------------------------------------------------------

# Каналы, к которым применяется критерий "рост не более 5% за шаг"
CRITERION_MAX_STEP_CHANNELS = {
    "расход на входе блендера 1",
    "расход на входе блендера 2",
}
MAX_STEP_RATIO = 0.05  # 5%


def _criterion_max_step(y: list[float], max_ratio: float = MAX_STEP_RATIO) -> tuple[list[float], bool]:
    """
    Критерий: каждое следующее значение не должно превышать предыдущее более чем на max_ratio.
    Если превышение найдено — возвращает сглаженный ряд и True.
    Исправление: заменяем выброс предыдущим значением * (1 + max_ratio).
    """
    if not y:
        return y, False

    corrected = list(y)
    changed = False

    for i in range(1, len(corrected)):
        prev = corrected[i - 1]
        curr = corrected[i]
        if prev > 0 and curr > prev * (1 + max_ratio):
            corrected[i] = round(prev * (1 + max_ratio), 4)
            changed = True
        elif prev <= 0 and curr > abs(prev) + 0.001:
            # если предыдущее ≤ 0, не ограничиваем
            pass

    return corrected, changed

    
# ---------------------------------------------------------------------------
# Определение структуры листа
# ---------------------------------------------------------------------------
def _detect_structure(df_raw: pd.DataFrame) -> dict:
    """
    Находит строку начала данных и индекс колонки Времени.
    Поддерживает форматы:
      - OGRP (row0=номера, row1=названия, row2=единицы, row3=данные)
      - Замещение (row0=названия, row1=единицы/подпись, row2=данные)
    """
    data_start = 3  # fallback
    # for i in range(min(8, len(df_raw))):
    #     val = df_raw.iloc[i, 0]
    #     try:
    #         f = float(str(val).replace(",", ".").strip())
    #         if f > 0:
    #             data_start = i
    #             break
    #     except (TypeError, ValueError):
    #         continue

    header_rows = data_start  # сколько строк заголовков

    # Строим нормализованные имена колонок из строки с названиями
    # Для OGRP: row0=номера(1,2,...), row1=названия → берём row1
    # Для Замещение: row0=названия → берём row0
    name_row_idx = 0
    unit_row_idx = None

    if header_rows >= 3:
        # Проверяем: если row[0] содержит числа типа "1","2" → OGRP-формат
        first_vals = [str(df_raw.iloc[0, c]).strip() for c in range(min(5, len(df_raw.columns)))]
        all_numeric = all(v.replace(".", "").isdigit() for v in first_vals if v not in ("nan", ""))
        if all_numeric:
            name_row_idx = 1
            unit_row_idx = 2
        else:
            name_row_idx = 0
            unit_row_idx = 1
    elif header_rows == 2:
        name_row_idx = 0
        unit_row_idx = 1
    else:
        name_row_idx = 0

    col_names = []
    col_units = []
    col_nums = []

    for c in range(len(df_raw.columns)):
        col_names.append(_clean(df_raw.iloc[name_row_idx, c]))
        col_units.append(_clean(df_raw.iloc[unit_row_idx, c]) if unit_row_idx is not None else "")
        # Номер канала: из row0 если OGRP, иначе просто col_idx+1
        if name_row_idx == 1:
            try:
                col_nums.append(int(float(str(df_raw.iloc[0, c]).strip())))
            except (ValueError, TypeError):
                col_nums.append(c + 1)
        else:
            col_nums.append(c + 1)

    # Ищем колонку времени
    time_col = 0
    for c, name in enumerate(col_names):
        for alias in TIME_ALIASES:
            if alias in name:
                time_col = c
                break

    logger.info(
        "Структура: data_start=%d, name_row=%d, unit_row=%s, time_col=%d, каналов=%d",
        data_start, name_row_idx, unit_row_idx, time_col, len(col_names),
    )

    return {
        "data_start": data_start,
        "time_col": time_col,
        "col_names": col_names,
        "col_units": col_units,
        "col_nums": col_nums,
    }


# ---------------------------------------------------------------------------
# Основная функция
# ---------------------------------------------------------------------------
def parse_excel_report(path: str) -> ParsedWorkbook:
    excel_file = pd.ExcelFile(path)
    logger.info("Листы: %s", excel_file.sheet_names)

    customer_sheet = _find_sheet_name(excel_file, SHEET_CUSTOMER)
    analyzer_sheet = _find_sheet_name(excel_file, SHEET_ANALYZER)

    if analyzer_sheet:
        source_sheet = analyzer_sheet
    elif customer_sheet:
        source_sheet = customer_sheet
    else:
        source_sheet = excel_file.sheet_names[0]
        logger.info("Листы 'Замещение' не найдены, читаем: '%s'", source_sheet)

    logger.info("Читаем лист: '%s'", source_sheet)

    df_raw = pd.read_excel(path, sheet_name=source_sheet, header=None)
    df_raw = df_raw.dropna(axis=0, how="all").reset_index(drop=True)
    logger.info("Размер: %d строк x %d колонок", len(df_raw), len(df_raw.columns))

    structure = _detect_structure(df_raw)
    data_start = structure["data_start"]
    time_col    = structure["time_col"]
    col_names   = structure["col_names"]
    col_units   = structure["col_units"]
    col_nums    = structure["col_nums"]

    df = df_raw.iloc[data_start:].reset_index(drop=True)
    logger.info("Строк данных: %d", len(df))

    # Время
    if time_col < len(df.columns):
        x = _parse_time_to_minutes(df.iloc[:, time_col])
    else:
        x = [round(i / 60.0, 4) for i in range(len(df))]

    # Строим серии по ВСЕМ каналам, кроме колонки Времени, в порядке col_nums
    charts: list[ParsedSeries] = []
    for c in range(len(df.columns)):
        if c == time_col:
            continue

        channel_num = col_nums[c]
        name = col_names[c] if col_names[c] not in ("nan", "None", "") else f"Канал {channel_num}"
        unit = col_units[c] if col_units[c] not in ("nan", "None", "") else ""

        raw = df.iloc[:, c]
        y_numeric = _coerce_numeric(raw).ffill().bfill().fillna(0.0)
        non_zero = (y_numeric != 0).sum()

        if non_zero > 0:
            logger.info("Канал №%d '%s': %d ненулевых", channel_num, name[:40], non_zero)

        y_list = _safe_float_list(y_numeric.tolist())

        # Применяем критерий если канал в списке
        name_lower = name.lower().strip()
        y_corrected: list[float] = []
        correction_applied = False
        if name_lower in CRITERION_MAX_STEP_CHANNELS:
            y_corrected, correction_applied = _criterion_max_step(y_list)
            if correction_applied:
                logger.info("Критерий 'max_step' сработал для канала '%s'", name)

        charts.append(ParsedSeries(
            channel_num=channel_num,
            name=name,
            unit=unit,
            x=x,
            y=y_list,
            y_corrected=y_corrected,
            correction_applied=correction_applied,
        ))

    # Сортируем по номеру канала (порядок из файла)
    charts.sort(key=lambda s: s.channel_num)

    logger.info("Итого каналов для отрисовки: %d", len(charts))
    return ParsedWorkbook(
        customer_sheet=customer_sheet,
        analyzer_sheet=analyzer_sheet,
        charts=charts,
    )