import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy import event
from sqlalchemy.pool import StaticPool

from app.main import app as fastapi_app
from app.core.database import get_session
import app.models.entities  # Ensure tables are registered on metadata


@pytest.fixture()
def session():
    """Yields a SQLModel session backed by a fresh in-memory SQLite database with FK enabled."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _enable_sqlite_fk(dbapi_conn, _record):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s
    engine.dispose()


@pytest.fixture()
def client(session):
    """Yields a FastAPI TestClient with the get_session dependency overridden."""
    def get_session_override():
        return session

    fastapi_app.dependency_overrides[get_session] = get_session_override
    with TestClient(fastapi_app) as test_client:
        yield test_client
    fastapi_app.dependency_overrides.clear()
