from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import ReportSessionStatus


class ReportSessionCreate(BaseModel):
    operation_date: date = Field(..., description="Дата проведения операции ГРП")
    operation_number: str = Field(..., min_length=1, max_length=64)
    well_name: str = Field(..., min_length=1, max_length=128)


class ReportSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    operation_date: date
    operation_number: str
    well_name: str
    original_filename: str | None
    status: ReportSessionStatus
    created_at: datetime
    updated_at: datetime


class ReportSessionDeleteResponse(BaseModel):
    id: int
    status: ReportSessionStatus
    detail: str


class UploadResponse(BaseModel):
    session_id: int
    filename: str
    size_bytes: int
    status: ReportSessionStatus
    detail: str = "Файл принят. Парсинг ещё не реализован."


class ChartTrace(BaseModel):
    name: str
    x: list[float | str] = Field(default_factory=list)
    y: list[float] = Field(default_factory=list)


class ChartFigure(BaseModel):
    id: str
    title: str
    traces: list[ChartTrace] = Field(default_factory=list)


class ChartsResponse(BaseModel):
    session_id: int
    figures: list[ChartFigure] = Field(default_factory=list)
    detail: str = "Графики ещё не реализованы — это заглушка."


class ChartSeriesResponse(BaseModel):
    channel_num: int = 0
    name: str
    unit: str = ""
    x: list[float]
    y: list[float]


class ParseResponse(BaseModel):
    session_id: int
    filename: str
    size_bytes: int
    status: ReportSessionStatus
    customer_sheet: str | None
    analyzer_sheet: str | None
    charts: list[ChartSeriesResponse]
