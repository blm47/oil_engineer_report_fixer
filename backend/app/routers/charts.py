from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ReportSession
from app.schemas import ChartsResponse

router = APIRouter(prefix="/sessions", tags=["charts"])


@router.get("/{session_id}/charts", response_model=ChartsResponse)
def get_charts(session_id: int, db: Session = Depends(get_db)) -> ChartsResponse:
    obj = db.get(ReportSession, session_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # Scaffold: real chart construction from parsed sheets is not implemented yet.
    return ChartsResponse(session_id=obj.id, figures=[])
