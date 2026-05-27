from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


SHEET_CUSTOMER = "Замещение (Заказчику)"
SHEET_ANALYZER = "Замещение (Анализатор)"


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


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(col).strip() for col in df.columns]
    return df


def _find_sheet_name(excel_file: pd.ExcelFile, target: str) -> str | None:
    target_lower = target.strip().lower()
    for sheet in excel_file.sheet_names:
        if str(sheet).strip().lower() == target_lower:
            return sheet
    for sheet in excel_file.sheet_names:
        if target_lower in str(sheet).strip().lower():
            return sheet
    return None


def _read_sheet(path: str, sheet_name: str) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name=sheet_name)
    df = _normalize_columns(df)
    df = df.dropna(axis=1, how="all")
    df = df.dropna(axis=0, how="all")
    return df.reset_index(drop=True)


def _coerce_numeric(series: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(series):
        return series.astype(float)
    cleaned = (
        series.astype(str)
        .str.replace(",", ".", regex=False)
        .str.replace(" ", "", regex=False)
        .replace({"nan": None, "None": None, "": None})
    )
    return pd.to_numeric(cleaned, errors="coerce")


def _find_time_column(df: pd.DataFrame) -> str | None:
    candidates = [
        "Время",
        "время",
        "Time",
        "TIME",
        "HHmmss",
        "HH:MM:SS",
    ]
    for candidate in candidates:
        if candidate in df.columns:
            return candidate

    for col in df.columns:
        col_lower = col.lower()
        if "врем" in col_lower or "time" in col_lower or "hh" in col_lower:
            return col
    return None


def _series_from_time_column(series: pd.Series, length: int) -> list[float]:
    if series is None:
        return [round(i / 60.0, 6) for i in range(length)]

    values = []
    parsed = pd.to_datetime(series, errors="coerce")
    if parsed.notna().sum() > max(3, int(length * 0.3)):
        start = parsed.dropna().iloc[0]
        for item in parsed:
            if pd.isna(item):
                values.append(None)
            else:
                values.append(round((item - start).total_seconds() / 60.0, 6))
        last = 0.0
        normalized = []
        for item in values:
            if item is None:
                last = round(last + 1 / 60.0, 6)
                normalized.append(last)
            else:
                last = float(item)
                normalized.append(last)
        return normalized

    numeric = _coerce_numeric(series)
    if numeric.notna().sum() > max(3, int(length * 0.3)):
        vals = numeric.fillna(method="ffill").fillna(method="bfill")
        return [float(v) for v in vals.tolist()]

    return [round(i / 60.0, 6) for i in range(length)]


def _pick_numeric_columns(df: pd.DataFrame, exclude: set[str]) -> list[str]:
    numeric_cols = []
    for col in df.columns:
        if col in exclude:
            continue
        converted = _coerce_numeric(df[col])
        non_na_ratio = converted.notna().mean() if len(converted) else 0
        if non_na_ratio >= 0.5:
            numeric_cols.append(col)
    return numeric_cols


def _extract_first_four_channels(df: pd.DataFrame) -> list[ParsedSeries]:
    time_col = _find_time_column(df)
    x = _series_from_time_column(df[time_col], len(df)) if time_col else [round(i / 60.0, 6) for i in range(len(df))]

    numeric_cols = _pick_numeric_columns(df, exclude={time_col} if time_col else set())
    first_three = numeric_cols[:3]

    chart_names = [
        "Давление 1",
        "Давление 2",
        "Затрубное давление",
    ]

    charts: list[ParsedSeries] = []
    for idx, col in enumerate(first_three):
        y = _coerce_numeric(df[col]).fillna(method="ffill").fillna(method="bfill").fillna(0.0)
        title = chart_names[idx] if idx < len(chart_names) else col
        charts.append(
            ParsedSeries(
                name=title,
                x=x,
                y=[float(v) for v in y.tolist()],
            )
        )
    return charts


def parse_excel_report(path: str) -> ParsedWorkbook:
    excel_file = pd.ExcelFile(path)

    customer_sheet = _find_sheet_name(excel_file, SHEET_CUSTOMER)
    analyzer_sheet = _find_sheet_name(excel_file, SHEET_ANALYZER)

    if not customer_sheet and not analyzer_sheet:
        raise ValueError(
            f"Не найдены листы '{SHEET_CUSTOMER}' или '{SHEET_ANALYZER}'"
        )

    source_sheet = analyzer_sheet or customer_sheet
    df = _read_sheet(path, source_sheet)

    charts = _extract_first_four_channels(df)

    time_chart = ParsedSeries(
        name="Время",
        x=[float(i) for i in range(len(charts[0].x if charts else df.index))],
        y=charts[0].x if charts else [round(i / 60.0, 6) for i in range(len(df))],
    )

    final_charts = [time_chart] + charts
    return ParsedWorkbook(
        customer_sheet=customer_sheet,
        analyzer_sheet=analyzer_sheet,
        charts=final_charts[:4],
    )