import pytest
from fastapi.testclient import TestClient


def test_live_returns_200(client: TestClient) -> None:
    """/live has no dependencies (not even the database) -- see FR-008."""
    response = client.get("/live")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_ready_reports_503_when_database_unreachable(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FR-008: /ready must reflect real database reachability, not just process startup.
    Forces the unreachable case explicitly (via monkeypatch) rather than assuming no database
    happens to be running in this environment -- a real database may well be up locally."""
    monkeypatch.setattr(
        "enterprise_rag_knowledge_assistant.api.routes.health.check_db_reachable",
        lambda: False,
    )
    response = client.get("/ready")
    assert response.status_code == 503
    assert response.json()["database"] is False
