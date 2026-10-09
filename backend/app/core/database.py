from typing import Generator
from sqlmodel import Session, create_engine, SQLModel
from app.core.config import settings

from sqlalchemy import event

# SQLite needs check_same_thread=False
connect_args = (
    {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
)

engine = create_engine(settings.DATABASE_URL, echo=False, connect_args=connect_args)

if settings.DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _enable_sqlite_fk(dbapi_conn, _record):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()


def init_db() -> None:
    """Creates database tables if they do not exist."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """Dependency for obtaining a database session."""
    with Session(engine) as session:
        yield session
