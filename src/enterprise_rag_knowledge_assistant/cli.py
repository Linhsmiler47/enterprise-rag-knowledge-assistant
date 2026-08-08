"""Operational commands, wired to Makefile targets (`make migrate`, `make ingest`).

Usage:
    python -m enterprise_rag_knowledge_assistant.cli init-db
    python -m enterprise_rag_knowledge_assistant.cli ingest <directory>
"""

import argparse
import logging
import sys
from pathlib import Path

from enterprise_rag_knowledge_assistant.config import get_settings
from enterprise_rag_knowledge_assistant.db import get_session, init_db
from enterprise_rag_knowledge_assistant.ingestion import ingest_directory
from enterprise_rag_knowledge_assistant.providers import LLMProvider

logging.basicConfig(level="INFO")
logger = logging.getLogger("cli")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init-db", help="Create the pgvector extension and tables")

    ingest_parser = subparsers.add_parser("ingest", help="Ingest a directory of documents")
    ingest_parser.add_argument("directory", type=Path)

    args = parser.parse_args()

    if args.command == "init-db":
        init_db()
        logger.info("database initialized")
        return 0

    if args.command == "ingest":
        if not args.directory.is_dir():
            logger.error("not a directory: %s", args.directory)
            return 1

        settings = get_settings()
        provider = LLMProvider(settings)
        with get_session() as session:
            results = ingest_directory(args.directory, session, provider)

        for r in results:
            logger.info("%-30s %-10s chunks=%d", r.filename, r.status, r.chunk_count)

        ingested = sum(1 for r in results if r.status == "ingested")
        unchanged = sum(1 for r in results if r.status == "unchanged")
        skipped = sum(1 for r in results if r.status == "skipped")
        logger.info(
            "done: %d ingested, %d unchanged, %d skipped", ingested, unchanged, skipped
        )
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
