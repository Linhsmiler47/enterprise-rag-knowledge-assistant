"""Application entrypoint."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from enterprise_rag_knowledge_assistant.api.routes.health import router as health_router
from enterprise_rag_knowledge_assistant.api.routes.query import router as query_router
from enterprise_rag_knowledge_assistant.config import get_settings

settings = get_settings()

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(settings.app_name)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Schema/extension creation is a deliberate operator step (`make migrate`), not done here on
    # every process start -- see docs/runbook.md.
    app.state.ready = True
    logger.info("startup complete", extra={"app_env": settings.app_env})
    yield
    app.state.ready = False


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(health_router)
app.include_router(query_router)
