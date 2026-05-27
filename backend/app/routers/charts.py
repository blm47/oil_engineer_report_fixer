from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ReportSession, ReportSessionStatus
from app.schemas import ChartFigure, ChartTrace, ChartsResponse

router = APIRouter(prefix="/sessions", tags=["charts"])

# Маппинг: name → chart id (стабильный, используется фронтом)
CHART_ID_MAP = {
    "Расход на выходе блендера 1": "flow_out_1",
    "Расход на выходе блендера 2": "flow_out_2",
    "Сумматор смеси с расхода 1 на выходе блендера": "sum_out_1",
    "Сумматор смеси с расхода 2 на выходе блендера": "sum_out_2",
}


@router.get("/{session_id}/charts", response_model=ChartsResponse)
def get_charts(session_id: int, db: Session = Depends(get_db)) -> ChartsResponse:
    obj = db.get(ReportSession, session_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    if obj.status not in (
        ReportSessionStatus.PARSED,
        ReportSessionStatus.REVIEWED,
    ):
        return ChartsResponse(
            session_id=obj.id,
            figures=[],
            detail=f"Файл ещё не распарсен (статус: {obj.status}). Сначала загрузите файл.",
        )

    # Данные хранятся в ParseResponse, который строится при upload.
    # Здесь нам нужно перечитать файл с диска.
    # Это временное решение — в следующем шаге добавим кэш/хранение в БД.
    from pathlib import Path
    import glob
    from app.config import get_settings
    from app.services.excel_parser import parse_excel_report

    settings = get_settings()
    session_dir = Path(settings.upload_dir) / str(session_id)

    excel_files = list(session_dir.glob("*.xlsx")) + list(session_dir.glob("*.xls"))
    if not excel_files:
        raise HTTPException(
            status_code=404,
            detail="Файл сессии не найден на диске. Загрузите файл повторно.",
        )

    # Берём последний загруженный файл
    latest = max(excel_files, key=lambda p: p.stat().st_mtime)

    try:
        parsed = parse_excel_report(str(latest))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Ошибка парсинга: {exc}") from exc

    figures: list[ChartFigure] = []
    for chart in parsed.charts:
        chart_id = CHART_ID_MAP.get(chart.name, chart.name.lower().replace(" ", "_"))
        figures.append(
            ChartFigure(
                id=chart_id,
                title=chart.name,
                traces=[
                    ChartTrace(name="Оригинал", x=chart.x, y=chart.y)
                ],
            )
        )

    return ChartsResponse(session_id=obj.id, figures=figures, detail="ok")