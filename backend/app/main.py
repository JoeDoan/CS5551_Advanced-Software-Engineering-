import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session
from app.core.config import settings
from app.core.database import engine
from app.core.security import ensure_auth_accounts
from app.core.startup import prepare_database, start_warmup
from app.api.v1.routes import router as api_v1_router

logger = logging.getLogger(__name__)


def _flag(name: str) -> bool:
    return os.getenv(name, "false").lower() in ("1", "true", "yes")


@asynccontextmanager
async def lifespan(app: FastAPI):
    report = prepare_database(
        engine,
        auto_seed=settings.AUTO_SEED,
        rebuild_stale=_flag("REBUILD_STALE_DB"),
    )
    app.state.startup_report = report
    try:
        with Session(engine) as session:
            ensure_auth_accounts(session)
    except Exception as exc:
        logger.error("Auth bootstrap failed: %s: %s", type(exc).__name__, exc)
    if _flag("DEMO_WARMUP") and report.ok:
        start_warmup(engine)
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="UMKC Scheduler: Smart Academic Course Scheduling API",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(api_v1_router, prefix=settings.API_V1_STR)


@app.get("/")
def root():
    return {
        "message": "Welcome to UMKC Scheduler API",
        "docs": f"{settings.API_V1_STR}/docs",
        "health": f"{settings.API_V1_STR}/health",
    }
