"""Health endpoints.

Three separate endpoints, three separate questions — see
learning/notes/00-app-baseline.md in the workspace root for why this distinction matters:

- /live   — is the process alive? (liveness — failing this gets the container restarted)
- /ready  — can it accept traffic right now? (readiness — failing this pulls it from the
            load balancer, without a restart). FR-008: gated on database reachability.
- /health — general status, including whether the vector index has any content (FR-008)
"""

from fastapi import APIRouter, Request, Response, status
from sqlalchemy import func

from enterprise_rag_knowledge_assistant.db import check_db_reachable, get_session
from enterprise_rag_knowledge_assistant.models import Chunk

router = APIRouter(tags=["health"])


@router.get("/live")
async def live() -> dict[str, str]:
    return {"status": "alive"}


@router.get("/ready")
async def ready(request: Request, response: Response) -> dict[str, bool]:
    app_ready = bool(getattr(request.app.state, "ready", False))
    db_ready = check_db_reachable()
    is_ready = app_ready and db_ready
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"ready": is_ready, "database": db_ready}


@router.get("/health")
async def health(request: Request) -> dict[str, object]:
    db_ready = check_db_reachable()
    indexed_chunk_count = 0
    if db_ready:
        with get_session() as session:
            indexed_chunk_count = session.query(func.count(Chunk.id)).scalar() or 0

    return {
        "status": "ok",
        "app": request.app.title,
        "ready": bool(getattr(request.app.state, "ready", False)),
        "database_reachable": db_ready,
        "indexed_chunks": indexed_chunk_count,
        "has_indexed_content": indexed_chunk_count > 0,
    }
