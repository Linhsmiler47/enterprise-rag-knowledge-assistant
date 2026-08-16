"""Phase 2: document upload, list/detail, manual ingestion trigger, delete."""

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


def _upload(client: TestClient, name: str, content: bytes, content_type: str = "text/markdown"):
    return client.post("/documents/upload", files={"file": (name, content, content_type)})


def test_upload_creates_document_with_uploaded_status(product_client: TestClient) -> None:
    response = _upload(product_client, "policy.md", b"Backups run daily.")
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "uploaded"
    assert body["original_filename"] == "policy.md"
    assert body["source"] == "upload"
    assert body["chunk_count"] == 0


def test_upload_rejects_unsupported_extension(product_client: TestClient) -> None:
    response = _upload(
        product_client, "notes.pdf", b"%PDF-1.4 fake", content_type="application/pdf"
    )
    assert response.status_code == 422


def test_upload_rejects_oversized_file(product_client: TestClient) -> None:
    huge = b"x" * 2_000_000  # over the 1MB default max_ingest_file_size_bytes
    response = _upload(product_client, "huge.md", huge)
    assert response.status_code == 413


def test_upload_rejects_empty_file(product_client: TestClient) -> None:
    response = _upload(product_client, "empty.md", b"")
    assert response.status_code == 422


def test_duplicate_content_upload_returns_existing_document(product_client: TestClient) -> None:
    first = _upload(product_client, "a.md", b"Same content, different name.")
    second = _upload(product_client, "b.md", b"Same content, different name.")
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]


def test_list_documents_includes_uploaded_document(product_client: TestClient) -> None:
    _upload(product_client, "listed.md", b"Some content for listing.")
    response = product_client.get("/documents")
    assert response.status_code == 200
    filenames = {d["original_filename"] for d in response.json()}
    assert "listed.md" in filenames


def test_get_document_detail_404_for_missing(product_client: TestClient) -> None:
    response = product_client.get("/documents/999999")
    assert response.status_code == 404


def test_get_document_detail_returns_uploaded_document(product_client: TestClient) -> None:
    uploaded = _upload(product_client, "detail.md", b"Detail content.").json()
    response = product_client.get(f"/documents/{uploaded['id']}")
    assert response.status_code == 200
    assert response.json()["original_filename"] == "detail.md"


def test_trigger_ingestion_transitions_to_ingested_with_chunks(product_client: TestClient) -> None:
    uploaded = _upload(product_client, "ingest-me.md", b"Database backups run daily.").json()

    response = product_client.post(f"/documents/{uploaded['id']}/ingest")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ingested"
    assert body["chunk_count"] >= 1
    assert body["ingestion_error"] is None


def test_trigger_ingestion_is_idempotent_when_already_ingested(product_client: TestClient) -> None:
    uploaded = _upload(product_client, "twice.md", b"Idempotent ingestion content.").json()
    first = product_client.post(f"/documents/{uploaded['id']}/ingest")
    second = product_client.post(f"/documents/{uploaded['id']}/ingest")

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["status"] == "ingested"
    assert second.json()["chunk_count"] == first.json()["chunk_count"]


def test_trigger_ingestion_404_for_missing_document(product_client: TestClient) -> None:
    response = product_client.post("/documents/999999/ingest")
    assert response.status_code == 404


def test_delete_document_removes_it(product_client: TestClient) -> None:
    uploaded = _upload(product_client, "delete-me.md", b"Content to delete.").json()

    delete_response = product_client.delete(f"/documents/{uploaded['id']}")
    assert delete_response.status_code == 204

    get_response = product_client.get(f"/documents/{uploaded['id']}")
    assert get_response.status_code == 404


def test_delete_document_404_for_missing(product_client: TestClient) -> None:
    response = product_client.delete("/documents/999999")
    assert response.status_code == 404


def test_query_after_upload_ingestion_cites_uploaded_document(product_client: TestClient) -> None:
    uploaded = _upload(
        product_client,
        "upload-backup-policy.md",
        b"Database backups run daily and are retained for thirty days.",
    ).json()
    ingest_response = product_client.post(f"/documents/{uploaded['id']}/ingest")
    assert ingest_response.json()["status"] == "ingested"

    query_response = product_client.post(
        "/query", json={"question": "How often do database backups run?"}
    )

    assert query_response.status_code == 200
    body = query_response.json()
    assert body["grounded"] is True
    assert any(c["document"] == "upload-backup-policy.md" for c in body["citations"])
