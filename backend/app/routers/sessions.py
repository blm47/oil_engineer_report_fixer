from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ReportSession, ReportSessionStatus
from app.schemas import (
    ReportSessionCreate,
    ReportSessionDeleteResponse,
    ReportSessionRead,
)

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=ReportSessionRead, status_code=status.HTTP_201_CREATED)
def create_session(payload: ReportSessionCreate, db: Session = Depends(get_db)) -> ReportSession:
    obj = ReportSession(
        operation_date=payload.operation_date,
        operation_number=payload.operation_number,
        well_name=payload.well_name,
        status=ReportSessionStatus.CREATED,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{session_id}", response_model=ReportSessionRead)
def get_session(session_id: int, db: Session = Depends(get_db)) -> ReportSession:
    obj = db.get(ReportSession, session_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return obj


@router.delete("/{session_id}", response_model=ReportSessionDeleteResponse)
def delete_session(session_id: int, db: Session = Depends(get_db)) -> ReportSessionDeleteResponse:
    obj = db.get(ReportSession, session_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    obj.status = ReportSessionStatus.CLOSED
    db.add(obj)
    db.commit()
    db.refresh(obj)

    return ReportSessionDeleteResponse(
        id=obj.id,
        status=obj.status,
        detail=(
            "Сессия помечена как закрытая. Очистка временных файлов будет реализована позже."
        ),
    )
