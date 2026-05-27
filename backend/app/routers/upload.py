from pathlib import Path
import shutil
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ReportSession, ReportSessionStatus
from app.schemas import UploadResponse, ChartSeriesResponse, ParseResponse
from app.services.excel_parser import parse_excel_report


router = APIRouter(prefix="/sessions", tags=["upload"])

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


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

    # NOTE: scaffold only — actual storage and Excel parsing arrive in a follow-up.
    content = await file.read()
    size_bytes = len(content)

    obj.original_filename = file.filename
    obj.status = ReportSessionStatus.UPLOADED
    db.add(obj)
    db.commit()
    db.refresh(obj)

    file_id = f"{uuid.uuid4()}-{file.filename}"
    saved_path = UPLOAD_DIR / file_id

    with saved_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        parsed = parse_excel_report(str(saved_path))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Ошибка парсинга Excel: {exc}") from exc


    return ParseResponse(
        session_id=obj.id,
        filename=file.filename or "",
        size_bytes=size_bytes,
        status=obj.status,
        customer_sheet=parsed.customer_sheet,
        analyzer_sheet=parsed.analyzer_sheet,
        charts=[
            ChartSeriesResponse(name=chart.name, x=chart.x, y=chart.y)
            for chart in parsed.charts
        ],
    )


router = APIRouter(prefix="/api", tags=["upload"])




@router.post("/upload", response_model=ParseResponse)
async def upload_excel(file: UploadFile = File(...)) -> ParseResponse:
    

    
    return ParseResponse(
        
    )