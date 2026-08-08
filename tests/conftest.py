import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker
from tests.fakes import FakeLLMProvider

from enterprise_rag_knowledge_assistant.db import check_db_reachable, get_db, make_engine
from enterprise_rag_knowledge_assistant.main import app
from enterprise_rag_knowledge_assistant.models import Base
from enterprise_rag_knowledge_assistant.providers import get_llm_provider


@pytest.fixture
def client() -> TestClient:
    """Plain client, no dependency overrides -- used by unit tests that intentionally exercise
    the "no database available" path (see tests/unit/test_health.py)."""
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def _db_engine():
    engine = make_engine()
    if not check_db_reachable():
        pytest.skip(
            "integration tests require a reachable database "
            "(DATABASE_URL) -- see docs/local-development.md"
        )
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(_db_engine) -> Session:
    """Real Postgres/pgvector session, truncated after every test for isolation."""
    session_factory = sessionmaker(bind=_db_engine, expire_on_commit=False)
    session = session_factory()
    yield session
    session.rollback()
    session.execute(text("TRUNCATE TABLE chunks, documents RESTART IDENTITY CASCADE"))
    session.commit()
    session.close()


@pytest.fixture
def fake_provider() -> FakeLLMProvider:
    return FakeLLMProvider()


@pytest.fixture
def api_client(db_session: Session, fake_provider: FakeLLMProvider) -> TestClient:
    """Integration-test client: real DB, fake (deterministic, no external service) LLM."""
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_llm_provider] = lambda: fake_provider
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
