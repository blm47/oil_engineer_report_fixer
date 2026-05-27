from __future__ import annotations

import logging
from dataclasses import dataclass

import pandas as pd

logger = logging.getLogger(__name__)

SHEET_CUSTOMER = "Замещение (Заказчику)"
SHEET_ANALYZER = "Замещение (Анализатор)"

# Имена искомых каналов (ищем по заголовку, а не по номеру столбца)
# Ключ — то что мы хотим отдать фронту, значение — варианты заголовков в файле
CHANNEL_ALIASES: dict[str, list[str]] = {
    "Расход на выходе блендера 1": [
        "расход на выходе 1",
        "расход выхода 1",
        "q вых 1",
        "q_вых1",
        "flowrate out 1",
        "flow out 1",
        "расход1",
        "q1",
    ],
    "Расход на выходе блендера 2": [
        "расход на выходе 2",
        "расход выхода 2",
        "q вых 2",
        "q_вых2",
        "flowrate out 2",
        "flow out 2",
        "расход2",
        "q2",
    ],
    "Сумматор смеси с расхода 1 на выходе блендера": [
        "сумматор смеси с расхода 1",
        "сумматор 1",
        "sum1",
        "sum 1",
        "объём выход 1",
        "v вых 1",
        "totalizer 1",
        "total out 1",
    ],
    "Сумматор смеси с расхода 2 на выходе блендера": [
        "сумматор смеси с расхода 2",
        "сумматор 2",
        "sum2",
        "sum 2",
        "объём выход 2",
        "v вых 2",
        "totalizer 2",
        "total out 2",
    ],
}

# Запасной вариант — позиции столбцов (0-based) если заголовки не найдены
# Согласно документу критериев: столбцы 5, 6, 8, 9 → индексы 4, 5, 7, 8
FALLBACK_COL_INDICES: dict[str, int] = {
    "Расход на выходе блендера 1": 4,
    "Расход на выходе блендера 2": 5,
    "Сумматор смеси с расхода 1 на выходе блендера": 7,
    "Сумматор смеси с расхода 2 на выходе блендера": 8,
}

TIME_ALIASES = ["время", "time", "hhmmss", "hh:mm:ss", "hh mm ss", "t,"]


@dataclass
class ParsedSeries:
    name: str
    x: list[float]
    y: list[float]


@dataclass
class ParsedWorkbook:
    customer_sheet: str | None
    analyzer_sheet: str | None
    charts: list[ParsedSeries]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _find_sheet_name(excel_file: pd.ExcelFile, target: str) -> str | None:
    target_lower = target.strip().lower()
    for sheet in excel_file.sheet_names:
        if str(sheet).strip().lower() == target_lower:
            return sheet
    for sheet in excel_file.sheet_names:
        if target_lower in str(sheet).strip().lower():
            return sheet
    return None


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


def _find_header_and_data_rows(df_raw: pd.DataFrame) -> tuple[int | None, int]:
    """
    Возвращает (header_row_idx, data_start_idx).
    Ищем строку, где col[0] является числом > 0 — это первая строка данных.
    Строка выше неё считается заголовком (если она есть).
    """
    for idx in range(len(df_raw)):
        val = df_raw.iloc[idx, 0]
        try:
            f = float(str(val).replace(",", ".").strip())
            if f > 0:
                header_row = idx - 1 if idx > 0 else None
                return header_row, idx
        except (TypeError, ValueError):
            continue
    # Если ничего не нашли — возвращаем 0 как data_start
    return None, 0


def _build_column_map(
    df_raw: pd.DataFrame,
    header_row: int | None,
    data_start: int,
) -> dict[str, int]:
    """
    Пытается построить маппинг имя_канала → индекс_столбца по заголовкам.
    Если заголовков нет, использует fallback по номерам столбцов.
    """
    col_map: dict[str, int] = {}

    if header_row is not None:
        headers = [
            str(v).strip().lower() if not (
                isinstance(v, float) and pd.isna(v)
            ) else ""
            for v in df_raw.iloc[header_row].tolist()
        ]
        logger.info("Заголовки листа: %s", headers)

        for channel_name, aliases in CHANNEL_ALIASES.items():
            for col_idx, col_header in enumerate(headers):
                for alias in aliases:
                    if alias in col_header or col_header in alias:
                        col_map[channel_name] = col_idx
                        break
                if channel_name in col_map:
                    break

    # Для каналов, которые не нашли по заголовку — используем fallback
    for channel_name, fallback_idx in FALLBACK_COL_INDICES.items():
        if channel_name not in col_map:
            col_map[channel_name] = fallback_idx
            logger.warning(
                "Канал '%s' не найден по заголовку, используем fallback col=%d",
                channel_name,
                fallback_idx,
            )

    return col_map


def _find_time_col_idx(
    df_raw: pd.DataFrame,
    header_row: int | None,
) -> int:
    """Ищет индекс столбца времени по заголовку, fallback = 0."""
    if header_row is not None:
        headers = [
            str(v).strip().lower() if not (isinstance(v, float) and pd.isna(v)) else ""
            for v in df_raw.iloc[header_row].tolist()
        ]
        for idx, h in enumerate(headers):
            for alias in TIME_ALIASES:
                if alias in h or h in alias:
                    return idx
    return 0


def _parse_time_to_minutes(series: pd.Series) -> list[float]:
    """
    Принимает числовой столбец времени и возвращает минуты от начала.
    Поддерживает форматы:
    - дробные минуты (0.01666 = 1 сек, 40.34 = 40 мин)
    - HHMMSS (120000 = 12:00:00)
    """
    numeric = _coerce_numeric(series)
    # ffill/bfill только для пробелов внутри, не трогаем начало
    numeric = numeric.bfill().ffill()
    values = [float(v) for v in numeric.tolist()]

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
        # Уже в минутах (или дробных секундах типа 0.01666)
        start = values[0]
        return [round(v - start, 4) for v in values]


# ---------------------------------------------------------------------------
# main entry point
# ---------------------------------------------------------------------------

def parse_excel_report(path: str) -> ParsedWorkbook:
    excel_file = pd.ExcelFile(path)

    customer_sheet = _find_sheet_name(excel_file, SHEET_CUSTOMER)
    analyzer_sheet = _find_sheet_name(excel_file, SHEET_ANALYZER)

    if not customer_sheet and not analyzer_sheet:
        raise ValueError(
            f"Не найдены листы '{SHEET_CUSTOMER}' или '{SHEET_ANALYZER}'. "
            f"Доступные листы: {excel_file.sheet_names}"
        )

    source_sheet = analyzer_sheet or customer_sheet
    logger.info("Читаем лист: %s", source_sheet)

    # Читаем без заголовков чтобы видеть всю структуру
    df_raw = pd.read_excel(path, sheet_name=source_sheet, header=None)
    df_raw = df_raw.dropna(axis=0, how="all").reset_index(drop=True)
    df_raw = df_raw.dropna(axis=1, how="all")

    logger.info("Размер листа после очистки NaN: %s строк x %s столбцов", len(df_raw), len(df_raw.columns))

    # --- диагностика первых строк ---
    for i in range(min(5, len(df_raw))):
        row_preview = [str(v)[:20] for v in df_raw.iloc[i].tolist()[:10]]
        logger.info("  row[%d]: %s", i, row_preview)

    header_row, data_start = _find_header_and_data_rows(df_raw)
    logger.info("header_row=%s  data_start=%d", header_row, data_start)

    time_col_idx = _find_time_col_idx(df_raw, header_row)
    col_map = _build_column_map(df_raw, header_row, data_start)

    logger.info("time_col_idx=%d  col_map=%s", time_col_idx, col_map)

    # Берём только строки данных
    df = df_raw.iloc[data_start:].reset_index(drop=True)

    logger.info("Строк данных: %d", len(df))
    logger.info("Первая строка данных: %s", df.iloc[0].tolist()[:10] if len(df) > 0 else "пусто")

    # Время
    if time_col_idx < len(df.columns):
        x = _parse_time_to_minutes(df.iloc[:, time_col_idx])
    else:
        x = [round(i / 60.0, 4) for i in range(len(df))]

    # Строим серии
    charts: list[ParsedSeries] = []
    for channel_name, col_idx in col_map.items():
        if col_idx >= len(df.columns):
            logger.warning("Канал '%s': col_idx=%d выходит за пределы (%d столбцов)", channel_name, col_idx, len(df.columns))
            charts.append(ParsedSeries(name=channel_name, x=x, y=[0.0] * len(x)))
            continue

        raw = df.iloc[:, col_idx]
        y_numeric = _coerce_numeric(raw)

        non_zero = (y_numeric.dropna() != 0).sum()
        logger.info("Канал '%s' col[%d]: %d ненулевых значений из %d", channel_name, col_idx, non_zero, len(y_numeric))

        y = y_numeric.ffill().bfill().fillna(0.0)
        charts.append(
            ParsedSeries(
                name=channel_name,
                x=x,
                y=[round(float(v), 4) for v in y.tolist()],
            )
        )

    return ParsedWorkbook(
        customer_sheet=customer_sheet,
        analyzer_sheet=analyzer_sheet,
        charts=charts,
    )