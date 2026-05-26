from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ReportSession, ReportSessionStatus
from app.schemas import UploadResponse

router = APIRouter(prefix="/sessions", tags=["upload"])


@router.post("/{session_id}/upload", response_model=UploadResponse)
async def upload_report(
    session_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> UploadResponse:
    obj = db.get(ReportSession, session_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # NOTE: scaffold only — actual storage and Excel parsing arrive in a follow-up.
    content = await file.read()
    size_bytes = len(content)

    obj.original_filename = file.filename
    obj.status = ReportSessionStatus.UPLOADED
    db.add(obj)
    db.commit()
    db.refresh(obj)

    return UploadResponse(
        session_id=obj.id,
        filename=file.filename or "",
        size_bytes=size_bytes,
        status=obj.status,
    )
