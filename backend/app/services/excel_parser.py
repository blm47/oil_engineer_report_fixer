from __future__ import annotations

import logging
import math
from dataclasses import dataclass

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Конфигурация листов (для старого формата "Замещение")
# ---------------------------------------------------------------------------
SHEET_CUSTOMER = "Замещение (Заказчику)"
SHEET_ANALYZER = "Замещение (Анализатор)"

# ---------------------------------------------------------------------------
# Целевые каналы: имя для фронта → варианты заголовков в файле (нижний регистр)
# Порядок важен — первое совпадение побеждает
# ---------------------------------------------------------------------------
CHANNEL_TARGETS: list[dict] = [
    {
        "name": "Стабилизатор глин концентрация (Основной)",
        "aliases": ["стабилизатор глин концентрация (основной)", "стаб глин конц осн"],
        "y_label": "л/м³",
    },
    {
        "name": "Стабилизатор глин расход (Основной)",
        "aliases": ["стабилизатор глин расход (основной)", "стаб глин расход осн"],
        "y_label": "л/мин",
    },
    {
        "name": "Стабилизатор глин сумматор (Основной)",
        "aliases": ["стабилизатор глин сумматор (основной)", "стаб глин сумм осн"],
        "y_label": "л",
    },
    {
        "name": "Стабилизатор глин концентрация (Резервный)",
        "aliases": ["стабилизатор глин концентрация (резервный)", "стаб глин конц рез"],
        "y_label": "л/м³",
    },
]

TIME_ALIASES = ["время", "time", "hhmmss", "hh:mm:ss", "hh mm ss"]


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------
@dataclass
class ParsedSeries:
    name: str
    x: list[float]
    y: list[float]
    y_label: str = ""


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


def _normalize(s: str) -> str:
    return str(s).strip().replace("\xa0", " ").replace("  ", " ").lower()


def _find_sheet_name(excel_file: pd.ExcelFile, target: str) -> str | None:
    target_norm = _normalize(target)
    for sheet in excel_file.sheet_names:
        if _normalize(sheet) == target_norm:
            return sheet
    for sheet in excel_file.sheet_names:
        if target_norm in _normalize(sheet) or _normalize(sheet) in target_norm:
            return sheet
    return None


# ---------------------------------------------------------------------------
# Определение структуры листа
# ---------------------------------------------------------------------------
def _detect_structure(df_raw: pd.DataFrame) -> dict:
    """
    Определяет структуру листа:
    - header_rows: сколько строк заголовков (1, 2 или 3)
    - data_start: индекс первой строки с данными
    - col_names: список нормализованных имён колонок
    - time_col: индекс колонки времени
    """
    # Ищем строку где col[0] — числовое значение > 0
    for data_start in range(min(10, len(df_raw))):
        val = df_raw.iloc[data_start, 0]
        try:
            f = float(str(val).replace(",", ".").strip())
            if f > 0:
                break
        except (TypeError, ValueError):
            continue
    else:
        data_start = 3  # fallback

    # Строки до data_start — заголовки
    # Собираем имена из последней строки заголовков (обычно это row data_start-1 или data_start-2)
    # Для OGRP: row[0]=номера, row[1]=названия, row[2]=единицы → берём row[1] как основное имя
    col_names = [""] * len(df_raw.columns)

    if data_start >= 2:
        # Берём строку с названиями (предпоследняя перед данными)
        name_row = data_start - 2
        unit_row = data_start - 1
        for col_idx in range(len(df_raw.columns)):
            name = _normalize(str(df_raw.iloc[name_row, col_idx]))
            unit = _normalize(str(df_raw.iloc[unit_row, col_idx]))
            # Склеиваем имя + единицу для более точного поиска
            col_names[col_idx] = name
    elif data_start == 1:
        name_row = 0
        for col_idx in range(len(df_raw.columns)):
            col_names[col_idx] = _normalize(str(df_raw.iloc[name_row, col_idx]))

    # Ищем колонку времени
    time_col = 0
    for col_idx, name in enumerate(col_names):
        for alias in TIME_ALIASES:
            if alias in name:
                time_col = col_idx
                break

    logger.info("Структура: data_start=%d, time_col=%d", data_start, time_col)
    logger.info("Заголовки колонок [0..9]: %s", col_names[:10])

    return {
        "data_start": data_start,
        "col_names": col_names,
        "time_col": time_col,
    }


def _find_channel_col(col_names: list[str], aliases: list[str]) -> int | None:
    """Ищет индекс колонки по списку псевдонимов."""
    for col_idx, name in enumerate(col_names):
        for alias in aliases:
            if _normalize(alias) in name or name in _normalize(alias):
                return col_idx
    return None


# ---------------------------------------------------------------------------
# Парсинг времени
# ---------------------------------------------------------------------------
def _parse_time_to_minutes(series: pd.Series) -> list[float]:
    numeric = _coerce_numeric(series).bfill().ffill().fillna(0.0)
    values = _safe_float_list(numeric.tolist())

    if not values:
        return []

    max_val = max(abs(v) for v in values)

    if max_val > 1000:
        # HHMMSS формат
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
        # Уже в минутах (дробные значения типа 0.018 = ~1 сек)
        start = values[0]
        return [round(v - start, 4) for v in values]


# ---------------------------------------------------------------------------
# Основная функция
# ---------------------------------------------------------------------------
def parse_excel_report(path: str) -> ParsedWorkbook:
    excel_file = pd.ExcelFile(path)
    logger.info("Листы в файле: %s", excel_file.sheet_names)

    customer_sheet = _find_sheet_name(excel_file, SHEET_CUSTOMER)
    analyzer_sheet = _find_sheet_name(excel_file, SHEET_ANALYZER)

    # Выбираем источник: Анализатор > Заказчику > первый лист
    if analyzer_sheet:
        source_sheet = analyzer_sheet
    elif customer_sheet:
        source_sheet = customer_sheet
    else:
        # Новый формат (OGRP и подобные) — берём первый лист
        source_sheet = excel_file.sheet_names[0]
        logger.info("Листы 'Замещение' не найдены, читаем первый лист: %s", source_sheet)

    logger.info("Читаем лист: '%s'", source_sheet)

    df_raw = pd.read_excel(path, sheet_name=source_sheet, header=None)
    df_raw = df_raw.dropna(axis=0, how="all").reset_index(drop=True)

    logger.info("Размер листа: %d строк x %d колонок", len(df_raw), len(df_raw.columns))

    structure = _detect_structure(df_raw)
    data_start = structure["data_start"]
    col_names = structure["col_names"]
    time_col = structure["time_col"]

    df = df_raw.iloc[data_start:].reset_index(drop=True)
    logger.info("Строк данных: %d", len(df))

    # Время
    if time_col < len(df.columns):
        x = _parse_time_to_minutes(df.iloc[:, time_col])
    else:
        x = [round(i / 60.0, 4) for i in range(len(df))]

    # Строим серии по целевым каналам
    charts: list[ParsedSeries] = []
    for target in CHANNEL_TARGETS:
        col_idx = _find_channel_col(col_names, target["aliases"])

        if col_idx is None:
            logger.warning("Канал '%s' не найден по заголовку", target["name"])
            charts.append(ParsedSeries(
                name=target["name"],
                x=x,
                y=[0.0] * len(x),
                y_label=target["y_label"],
            ))
            continue

        if col_idx >= len(df.columns):
            logger.warning("Канал '%s': col_idx=%d за пределами (%d колонок)", target["name"], col_idx, len(df.columns))
            charts.append(ParsedSeries(name=target["name"], x=x, y=[0.0] * len(x), y_label=target["y_label"]))
            continue

        raw = df.iloc[:, col_idx]
        y_numeric = _coerce_numeric(raw).ffill().bfill().fillna(0.0)
        non_zero = (y_numeric != 0).sum()
        logger.info("Канал '%s' col[%d]: %d ненулевых из %d", target["name"], col_idx, non_zero, len(y_numeric))

        charts.append(ParsedSeries(
            name=target["name"],
            x=x,
            y=_safe_float_list(y_numeric.tolist()),
            y_label=target["y_label"],
        ))

    return ParsedWorkbook(
        customer_sheet=customer_sheet,
        analyzer_sheet=analyzer_sheet,
        charts=charts,
    )