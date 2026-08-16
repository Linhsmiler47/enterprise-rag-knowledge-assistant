"""Object storage boundary for uploaded documents (see docs/adr/0011-phase2-stack.md).

Narrow, like providers.py: MinIO speaks the S3 API, so any S3-compatible endpoint works with
this same client -- only endpoint/keys differ, all set via config.py. Never stores anything
under a client-supplied path; object keys are always server-generated (see api/routes/documents.py).
"""

from functools import lru_cache
from io import BytesIO

from minio import Minio
from minio.error import S3Error

from enterprise_rag_knowledge_assistant.config import Settings, get_settings


class ObjectStorage:
    def __init__(self, settings: Settings) -> None:
        self._client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        self._bucket = settings.minio_bucket
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        if not self._client.bucket_exists(self._bucket):
            self._client.make_bucket(self._bucket)

    def put_object(self, object_key: str, data: bytes, content_type: str) -> None:
        self._client.put_object(
            self._bucket, object_key, BytesIO(data), length=len(data), content_type=content_type
        )

    def get_object(self, object_key: str) -> bytes:
        response = self._client.get_object(self._bucket, object_key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def delete_object(self, object_key: str) -> None:
        try:
            self._client.remove_object(self._bucket, object_key)
        except S3Error as exc:
            if exc.code != "NoSuchKey":
                raise

@lru_cache
def get_storage() -> ObjectStorage:
    """FastAPI dependency -- overridden with a fake in tests via app.dependency_overrides."""
    return ObjectStorage(get_settings())


def check_storage_reachable(settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    try:
        client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        client.bucket_exists(settings.minio_bucket)
        return True
    except Exception:
        return False
