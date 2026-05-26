import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import Base, engine
from app.routers import charts, sessions, upload

logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title="Oil Engineer Report Fixer API",
    version="0.1.0",
    description=(
        "Backend для разбора и предпросмотра корректировок Excel-отчётов по операциям ГРП."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Skipping create_all on startup: %s", exc)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(sessions.router)
app.include_router(upload.router)
app.include_router(charts.router)
