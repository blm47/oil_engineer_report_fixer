from pathlib import Path
import shutil
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import ReportSession, ReportSessionStatus
from app.schemas import ChartSeriesResponse, ParseResponse
from app.services.excel_parser import parse_excel_report

router = APIRouter(prefix="/sessions", tags=["upload"])

settings = get_settings()


def _get_upload_dir() -> Path:
    p = Path(settings.upload_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


@router.post("/{session_id}/upload", response_model=ParseResponse)
async def upload_report(
    session_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> ParseResponse:
    obj = db.get(ReportSession, session_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    if not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Нужен Excel файл .xlsx/.xls")

    # Сохраняем файл в папку, уникальную для сессии
    session_dir = _get_upload_dir() / str(session_id)
    session_dir.mkdir(parents=True, exist_ok=True)
    saved_path = session_dir / f"{uuid.uuid4().hex}_{file.filename}"

    content = await file.read()
    size_bytes = len(content)

    with saved_path.open("wb") as buffer:
        buffer.write(content)

    try:
        parsed = parse_excel_report(str(saved_path))
    except Exception as exc:
        obj.status = ReportSessionStatus.FAILED
        db.add(obj)
        db.commit()
        raise HTTPException(status_code=400, detail=f"Ошибка парсинга Excel: {exc}") from exc

    obj.original_filename = file.filename
    obj.status = ReportSessionStatus.PARSED
    db.add(obj)
    db.commit()
    db.refresh(obj)

    return ParseResponse(
        session_id=obj.id,
        filename=file.filename or "",
        size_bytes=size_bytes,
        status=obj.status,
        customer_sheet=parsed.customer_sheet,
        analyzer_sheet=parsed.analyzer_sheet,
        charts=[
            ChartSeriesResponse(name=chart.name, x=chart.x, y=chart.y, y_label=chart.y_label)
            for chart in parsed.charts
        ],
    )