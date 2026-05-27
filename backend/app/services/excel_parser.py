from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

SHEET_CUSTOMER = "Замещение (Заказчику)"
SHEET_ANALYZER = "Замещение (Анализатор)"

# Индексы колонок (0-based) согласно документу критериев
COL_TIME = 0          # Время
COL_FLOW_OUT_1 = 4   # Расход на выходе 1 (5-й столбец)
COL_FLOW_OUT_2 = 5   # Расход на выходе 2 (6-й столбец)
COL_SUM_OUT_1 = 7    # Сумматор смеси с расхода 1 (8-й столбец)
COL_SUM_OUT_2 = 8    # Сумматор смеси с расхода 2 (9-й столбец)

CHART_COLUMNS = {
    "Расход на выходе блендера 1": COL_FLOW_OUT_1,
    "Расход на выходе блендера 2": COL_FLOW_OUT_2,
    "Сумматор смеси с расхода 1 на выходе блендера": COL_SUM_OUT_1,
    "Сумматор смеси с расхода 2 на выходе блендера": COL_SUM_OUT_2,
}


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


def _find_sheet_name(excel_file: pd.ExcelFile, target: str) -> str | None:
    target_lower = target.strip().lower()
    for sheet in excel_file.sheet_names:
        if str(sheet).strip().lower() == target_lower:
            return sheet
    for sheet in excel_file.sheet_names:
        if target_lower in str(sheet).strip().lower():
            return sheet
    return None


def _read_sheet_raw(path: str, sheet_name: str) -> pd.DataFrame:
    """Читает лист без заголовков — данные начинаются с какой-то строки."""
    df = pd.read_excel(path, sheet_name=sheet_name, header=None)
    # Убираем строки где все значения NaN
    df = df.dropna(axis=0, how="all").reset_index(drop=True)
    return df


def _find_data_start_row(df: pd.DataFrame) -> int:
    """Ищет строку, с которой начинаются числовые данные (время > 0)."""
    time_col = df.iloc[:, COL_TIME]
    for idx, val in time_col.items():
        try:
            f = float(val)
            if f > 0:
                return int(idx)
        except (TypeError, ValueError):
            continue
    return 0


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


def _parse_time_to_minutes(series: pd.Series) -> list[float]:
    """
    Конвертирует время из формата HHmmss (секунды кодированы как дробное число,
    например 1/60 = 0.01666...) или числового формата в минуты от начала.
    """
    numeric = _coerce_numeric(series).fillna(method="ffill").fillna(0.0)
    values = numeric.tolist()

    # Определяем, это HHmmss-like (большие числа типа 120000) или уже дробные секунды
    max_val = max(abs(v) for v in values if v is not None) if values else 0
    if max_val > 1000:
        # Формат HHMMSS → конвертируем в минуты
        result = []
        for v in values:
            v = float(v)
            hh = int(v) // 10000
            mm = (int(v) % 10000) // 100
            ss = int(v) % 100
            result.append(round(hh * 60 + mm + ss / 60.0, 4))
        # Нормализуем от нуля
        if result:
            start = result[0]
            result = [round(t - start, 4) for t in result]
        return result
    else:
        # Уже в минутах или дробные значения (0.0166 = 1 сек)
        start = values[0] if values else 0.0
        return [round(float(v) - float(start), 4) for v in values]


def _extract_charts(df: pd.DataFrame) -> list[ParsedSeries]:
    time_series = _parse_time_to_minutes(df.iloc[:, COL_TIME])

    charts: list[ParsedSeries] = []
    for name, col_idx in CHART_COLUMNS.items():
        if col_idx >= len(df.columns):
            # колонка отсутствует в файле — добавляем нули
            charts.append(ParsedSeries(name=name, x=time_series, y=[0.0] * len(time_series)))
            continue

        raw = df.iloc[:, col_idx]
        y = _coerce_numeric(raw).fillna(method="ffill").fillna(method="bfill").fillna(0.0)
        charts.append(
            ParsedSeries(
                name=name,
                x=time_series,
                y=[round(float(v), 4) for v in y.tolist()],
            )
        )
    return charts


def parse_excel_report(path: str) -> ParsedWorkbook:
    excel_file = pd.ExcelFile(path)

    customer_sheet = _find_sheet_name(excel_file, SHEET_CUSTOMER)
    analyzer_sheet = _find_sheet_name(excel_file, SHEET_ANALYZER)

    if not customer_sheet and not analyzer_sheet:
        raise ValueError(
            f"Не найдены листы '{SHEET_CUSTOMER}' или '{SHEET_ANALYZER}'. "
            f"Доступные листы: {excel_file.sheet_names}"
        )

    # Приоритет: Анализатор → Заказчику
    source_sheet = analyzer_sheet or customer_sheet
    df_raw = _read_sheet_raw(path, source_sheet)

    data_start = _find_data_start_row(df_raw)
    df = df_raw.iloc[data_start:].reset_index(drop=True)

    charts = _extract_charts(df)

    return ParsedWorkbook(
        customer_sheet=customer_sheet,
        analyzer_sheet=analyzer_sheet,
        charts=charts,
    )