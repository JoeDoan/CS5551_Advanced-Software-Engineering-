import pytest
from sqlmodel import SQLModel, Session, create_engine


@pytest.fixture()
def session():
    """Yields a SQLModel session backed by a fresh in-memory SQLite database."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()
