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
    """Очистка для ХРАНЕНИЯ — сохраняет регистр."""
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


def _detect_structure(df_raw: pd.DataFrame) -> dict:
    """Определяет строки заголовков, единиц, номеров каналов и начало данных."""
    n_rows, n_cols = df_raw.shape

    data_start = 3
    for i in range(min(6, n_rows)):
        try:
            numeric_count = sum(
                1 for v in df_raw.iloc[i]
                if pd.to_numeric(str(v).replace(",", "."), errors="coerce") is not None
                and str(v).strip() not in ("", "nan")
            )
            if numeric_count > n_cols * 0.5:
                data_start = i
                break
        except Exception:
            continue

    header_rows = data_start

    name_row_idx = 0
    unit_row_idx = None

    if header_rows >= 3:
        name_row_idx = 1
        unit_row_idx = 2
    elif header_rows == 2:
        name_row_idx = 0
        unit_row_idx = 1
    else:
        name_row_idx = 0
        unit_row_idx = 1

    col_names = []
    col_units = []
    col_nums  = []

    for c in range(n_cols):
        col_names.append(_clean(df_raw.iloc[name_row_idx, c]))
        col_units.append(_clean(df_raw.iloc[unit_row_idx, c]) if unit_row_idx is not None else "")

        if name_row_idx == 1:
            try:
                col_nums.append(int(float(str(df_raw.iloc[0, c]).strip())))
            except (ValueError, TypeError):
                col_nums.append(c + 1)
        else:
            col_nums.append(c + 1)

    time_col = 0
    for c, name in enumerate(col_names):
        for alias in TIME_ALIASES:
            if alias in _normalize(name):
                time_col = c
                break

    logger.info(
        "Структура: data_start=%d, name_row=%d, unit_row=%s, time_col=%d, каналов=%d",
        data_start, name_row_idx, unit_row_idx, time_col, len(col_names),
    )

    return {
        "data_start": data_start,
        "time_col":   time_col,
        "col_names":  col_names,
        "col_units":  col_units,
        "col_nums":   col_nums,
    }


def _parse_time_to_minutes(series: pd.Series) -> list[float]:
    parsed = pd.to_datetime(series, format="%H:%M:%S", errors="coerce")
    if parsed.notna().sum() > len(series) * 0.3:
        start = parsed.dropna().iloc[0]
        result = []
        for v in parsed:
            if pd.isna(v):
                result.append(result[-1] + (1 / 60.0) if result else 0.0)
            else:
                result.append(round((v - start).total_seconds() / 60.0, 4))
        return result

    numeric = _coerce_numeric(series)
    if numeric.notna().sum() > len(series) * 0.3:
        return [round(float(v), 4) for v in numeric.fillna(method="ffill").fillna(0).tolist()]

    return [round(i / 60.0, 4) for i in range(len(series))]


# ---------------------------------------------------------------------------
# Критерии
# ---------------------------------------------------------------------------

# ── Критерий 1: рост расхода не более 5% за шаг ──────────────────────────
CRITERION_MAX_STEP_CHANNELS = {
    "расход на входе блендера 1",
    "расход на входе блендера 2",
}
MAX_STEP_RATIO = 0.05


def _criterion_max_step(
    y: list[float],
    max_ratio: float = MAX_STEP_RATIO,
) -> tuple[list[float], bool]:
    """Каждое следующее значение не должно превышать предыдущее более чем на max_ratio."""
    if not y:
        return y, False
    corrected = list(y)
    changed = False
    for i in range(1, len(corrected)):
        prev, curr = corrected[i - 1], corrected[i]
        if prev > 0 and curr > prev * (1 + max_ratio):
            corrected[i] = round(prev * (1 + max_ratio), 4)
            changed = True
    return corrected, changed


# ── Критерий 2: хим. реагенты (стабилизатор глин, каналы 41-43) ──────────

# Эталонная концентрация стабилизатора глин (л/м³) и допуск ±5%
STABILIZER_CONC_REF  = 2.0
STABILIZER_CONC_TOL  = 0.05

# Тройки каналов хим. реагентов: (канал_конц, канал_расход, канал_сумматор)
# Ключ — нижний регистр части имени, общей для тройки
CHEM_CHANNEL_GROUPS: list[dict] = [
    {
        "key":       "стабилизатор глин",
        "conc_num":  41,
        "flow_num":  42,
        "summ_num":  43,
        "conc_ref":  STABILIZER_CONC_REF,
        "conc_tol":  STABILIZER_CONC_TOL,
    },
    {
        "key":       "стабилизатор глин",
        "conc_num":  41,
        "flow_num":  42,
        "summ_num":  43,
        "conc_ref":  STABILIZER_CONC_REF,
        "conc_tol":  STABILIZER_CONC_TOL,
    },
]

# Номер канала общего расхода (Расход на входе блендера 1)
MAIN_FLOW_CHANNEL_NUM = 11


def _criterion_chem_reagent(
    y_conc: list[float],
    y_flow: list[float],
    y_summ: list[float],
    y_main_flow: list[float],
    conc_ref: float,
    conc_tol: float,
) -> tuple[list[float], list[float], list[float], bool]:
    """
    Коррекция тройки каналов хим. реагента:

    1. Концентрация: зажимаем в [conc_ref*(1-tol), conc_ref*(1+tol)].
       Если ch_main_flow == 0 — концентрация тоже 0.
    2. Расход: пересчитываем из скорректированной концентрации * main_flow.
    3. Сумматор: накапливаем расход / 60; после конца активной зоны — держим
       последнее значение.

    Возвращает (conc_corr, flow_corr, summ_corr, changed).
    """
    n = len(y_conc)
    conc_lo = round(conc_ref * (1 - conc_tol), 6)
    conc_hi = round(conc_ref * (1 + conc_tol), 6)

    conc_corr: list[float] = []
    flow_corr: list[float] = []
    summ_corr: list[float] = []
    changed = False
    cumsum = 0.0

    for i in range(n):
        mf = y_main_flow[i] if i < len(y_main_flow) else 0.0
        c  = y_conc[i] if i < len(y_conc) else 0.0

        # Концентрация
        if mf <= 0:
            cc = 0.0
        else:
            if c > conc_hi:
                cc = conc_hi
                changed = True
            elif 0 < c < conc_lo:
                cc = conc_lo
                changed = True
            elif c == 0:
                # нет сигнала в активной зоне — подставляем эталон
                cc = conc_ref
                changed = True
            else:
                cc = c

        # Расход
        fc = round(cc * mf, 4)

        # Сумматор
        if mf > 0:
            cumsum = round(cumsum + fc / 60.0, 4)
        # если mf == 0 — кумулятив не меняется (тянем последнее значение)

        # Проверяем расход
        orig_fc = y_flow[i] if i < len(y_flow) else 0.0
        if abs(fc - orig_fc) > 1e-6:
            changed = True

        conc_corr.append(round(cc, 4))
        flow_corr.append(fc)
        summ_corr.append(cumsum)

    return conc_corr, flow_corr, summ_corr, changed


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

    structure  = _detect_structure(df_raw)
    data_start = structure["data_start"]
    time_col   = structure["time_col"]
    col_names  = structure["col_names"]
    col_units  = structure["col_units"]
    col_nums   = structure["col_nums"]

    df = df_raw.iloc[data_start:].reset_index(drop=True)
    logger.info("Строк данных: %d", len(df))

    # Время
    if time_col < len(df.columns):
        x = _parse_time_to_minutes(df.iloc[:, time_col])
    else:
        x = [round(i / 60.0, 4) for i in range(len(df))]

    # ── Шаг 1: парсим все каналы в сырые серии ────────────────────────────
    raw_by_num: dict[int, list[float]] = {}   # channel_num -> y_list
    charts_meta: list[dict] = []              # сохраняем мета для сборки ParsedSeries

    for c in range(len(df.columns)):
        if c == time_col:
            continue

        channel_num = col_nums[c]
        name = col_names[c] if col_names[c] not in ("nan", "None", "") else f"Канал {channel_num}"
        unit = col_units[c] if col_units[c] not in ("nan", "None", "") else ""

        raw        = df.iloc[:, c]
        y_numeric  = _coerce_numeric(raw).ffill().bfill().fillna(0.0)
        y_list     = _safe_float_list(y_numeric.tolist())

        raw_by_num[channel_num] = y_list
        charts_meta.append({
            "channel_num": channel_num,
            "name":        name,
            "unit":        unit,
            "y":           y_list,
        })

        non_zero = sum(1 for v in y_list if v != 0)
        if non_zero > 0:
            logger.info("Канал №%d '%s': %d ненулевых", channel_num, name[:40], non_zero)

    # ── Шаг 2: применяем критерии ─────────────────────────────────────────
    corrections: dict[int, tuple[list[float], bool]] = {}
    # {channel_num: (y_corrected, correction_applied)}

    # Критерий 1 — рост расхода
    for meta in charts_meta:
        name_lower = _normalize(meta["name"])
        if name_lower in CRITERION_MAX_STEP_CHANNELS:
            y_corr, applied = _criterion_max_step(meta["y"])
            corrections[meta["channel_num"]] = (y_corr, applied)
            if applied:
                logger.info("Критерий 'max_step' сработал для '%s'", meta["name"])

    # Критерий 2 — хим. реагенты (тройки каналов)
    main_flow = raw_by_num.get(MAIN_FLOW_CHANNEL_NUM, [0.0] * len(x))

    for group in CHEM_CHANNEL_GROUPS:
        cn_c = group["conc_num"]
        cn_f = group["flow_num"]
        cn_s = group["summ_num"]

        y_c = raw_by_num.get(cn_c, [0.0] * len(x))
        y_f = raw_by_num.get(cn_f, [0.0] * len(x))
        y_s = raw_by_num.get(cn_s, [0.0] * len(x))

        c_corr, f_corr, s_corr, changed = _criterion_chem_reagent(
            y_conc=y_c,
            y_flow=y_f,
            y_summ=y_s,
            y_main_flow=main_flow,
            conc_ref=group["conc_ref"],
            conc_tol=group["conc_tol"],
        )

        corrections[cn_c] = (c_corr, changed)
        corrections[cn_f] = (f_corr, changed)
        corrections[cn_s] = (s_corr, changed)

        if changed:
            logger.info(
                "Критерий 'chem_reagent' сработал для группы '%s' (каналы %d/%d/%d)",
                group["key"], cn_c, cn_f, cn_s,
            )

    # ── Шаг 3: собираем ParsedSeries ──────────────────────────────────────
    charts: list[ParsedSeries] = []
    for meta in charts_meta:
        ch_num = meta["channel_num"]
        y_corr, applied = corrections.get(ch_num, ([], False))

        charts.append(ParsedSeries(
            channel_num=ch_num,
            name=meta["name"],
            unit=meta["unit"],
            x=x,
            y=meta["y"],
            y_corrected=y_corr,
            correction_applied=applied,
        ))

    charts.sort(key=lambda s: s.channel_num)
    logger.info("Итого каналов для отрисовки: %d", len(charts))

    return ParsedWorkbook(
        customer_sheet=customer_sheet,
        analyzer_sheet=analyzer_sheet,
        charts=charts,
    )