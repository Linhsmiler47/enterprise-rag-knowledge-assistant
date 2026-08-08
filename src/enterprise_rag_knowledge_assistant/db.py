"""Database engine/session setup."""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from enterprise_rag_knowledge_assistant.config import Settings, get_settings
from enterprise_rag_knowledge_assistant.models import Base


def make_engine(settings: Settings | None = None):
    settings = settings or get_settings()
    return create_engine(settings.database_url, pool_pre_ping=True)


_engine = None
_SessionLocal: sessionmaker | None = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = make_engine()
    return _engine


def _get_session_factory() -> sessionmaker:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=_get_engine(), expire_on_commit=False)
    return _SessionLocal


@contextmanager
def get_session() -> Iterator[Session]:
    """Use directly (`with get_session() as session:`) outside of FastAPI request handling."""
    session = _get_session_factory()()
    try:
        yield session
    finally:
        session.close()


def get_db() -> Iterator[Session]:
    """FastAPI dependency -- overridden with a test session via app.dependency_overrides."""
    with get_session() as session:
        yield session


def init_db() -> None:
    """Create the pgvector extension and all tables. Idempotent."""
    engine = _get_engine()
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(engine)


def check_db_reachable() -> bool:
    try:
        engine = _get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
