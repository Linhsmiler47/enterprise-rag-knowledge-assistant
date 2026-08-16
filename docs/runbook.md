# Runbook

## Start / stop (local)

```bash
make dev     # start app + Postgres/pgvector + MinIO via Docker Compose
make down    # stop and remove
```

Product UI (Phase 2, optional): `cd frontend && npm install && npm run dev` — see
[`docs/local-development.md`](local-development.md#product-ui-workflow-phase-2-no-cli-needed).

## Deploy

```bash
git tag v0.1.0 && git push --tags   # triggers release.yml -> builds + pushes image, immutable digest
# deploy.yml: main -> dev automatically; production requires the tag + GitHub Environment approval
```

## Smoke test

```bash
./scripts/smoke-test.sh https://<deployed-url>
```

Checks `/live`, `/ready`, `/health` all respond 200. A real deployment verification also confirms
`/health`'s `indexed_chunks > 0` — an app that's "ready" but has never been seeded is not actually
useful yet (see the cost/persistence tradeoff in
[ADR-0007](adr/0007-demo-persistence-cost-tradeoff.md) for why the demo re-seeds on every start).

## Rollback

Container Apps keeps prior revisions. Rollback is a traffic-split change to the previous known-
good revision, not a rebuild:

```bash
az containerapp revision list -n <app-name> -g <resource-group> -o table
az containerapp ingress traffic set -n <app-name> -g <resource-group> \
  --revision-weight <previous-revision>=100
```

Verify with the smoke test script immediately after.

## Common failure scenarios

| Symptom | Likely cause | Fix |
|---|---|---|
| `/ready` returns 503 | Database unreachable | Check `DATABASE_URL`; check the DB container/managed instance is running |
| `/health` shows `indexed_chunks: 0` | Ingestion never ran (fresh deploy or ephemeral-storage restart) | `make ingest` (local) or trigger the app's startup seed (demo deployment — see ADR-0007) |
| `/query` always returns `grounded: false` | Retrieval threshold too high for the embedding model in use, or index is genuinely empty | Check `/health`'s `indexed_chunks`; check `RETRIEVAL_SIMILARITY_THRESHOLD` |
| Ollama connection refused | Local Ollama not running / wrong `LLM_BASE_URL` | Start Ollama (`ollama serve`) or use the `docker-compose.ollama.yml` slice |
| Ingestion silently skips a file | Unsupported extension (only `.md`/`.txt` — [ADR-0003](adr/0003-ingestion-format-scope.md)) | Expected behavior, not a bug — check the ingestion log line |
| `POST /documents/upload` returns a connection error | MinIO not running / wrong `MINIO_ENDPOINT` | Confirm `make dev` is up; `curl localhost:9000/minio/health/live` |
| A document stays `status: "failed"` after triggering ingest | LLM provider unreachable, or the file isn't valid UTF-8 text | Check the document's `ingestion_error` field (safe summary) and the app's server logs (full traceback, never exposed to the client — ADR-0008); re-trigger ingest once the provider is reachable |
| `column documents.object_key does not exist` (or similar) after pulling a change | The local dev DB has an old schema — there's no migration tool yet (no Alembic), `make migrate` only creates missing tables, it doesn't alter existing ones | Drop and recreate the local tables: `DROP TABLE chunks, documents CASCADE;` then `make migrate`. Safe — local dev/demo data only (ADR-0007's ephemeral-data precedent). |

## Database troubleshooting

```bash
# Connect directly
psql "$DATABASE_URL"

# Check row counts
SELECT count(*) FROM documents;
SELECT count(*) FROM chunks;

# Re-run migration (idempotent -- safe to re-run)
make migrate
```

## Cost shutdown procedure

See the incubating workspace's `docs/playbooks/incident-cost-runaway.md` for the general
procedure, if this project is still incubating there. Project-specific:

```bash
# Scale the demo Container App to zero immediately
az containerapp update -n <app-name> -g <resource-group> --min-replicas 0 --max-replicas 0

# Full teardown (see docs/deployment.md for what this removes)
cd infra/environments/dev && terraform destroy
```
