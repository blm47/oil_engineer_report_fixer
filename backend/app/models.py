from datetime import date, datetime
from enum import Enum as PyEnum

from sqlalchemy import Date, DateTime, Enum, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ReportSessionStatus(str, PyEnum):
    CREATED = "created"
    UPLOADED = "uploaded"
    PARSED = "parsed"
    REVIEWED = "reviewed"
    CLOSED = "closed"
    FAILED = "failed"


class ReportSession(Base):
    """Метаданные сессии работы инженера с одним отчётом операции ГРП.

    Сам Excel-файл хранится во временном хранилище и не попадает в БД.
    """

    __tablename__ = "report_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    operation_date: Mapped[date] = mapped_column(Date, nullable=False)
    operation_number: Mapped[str] = mapped_column(String(64), nullable=False)
    well_name: Mapped[str] = mapped_column(String(128), nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[ReportSessionStatus] = mapped_column(
        Enum(ReportSessionStatus, name="report_session_status"),
        default=ReportSessionStatus.CREATED,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
