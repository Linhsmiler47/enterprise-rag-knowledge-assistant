# ADR-0007 — Demo Persistence / Cost Tradeoff

**Status:** Accepted

## Context

Managed Azure Database for PostgreSQL Flexible Server (even the smallest Burstable tier) costs
real money every month it exists, whether or not anyone is looking at the demo. A personal
portfolio project's honest goal is "recruiter clicks link, sees it work" — not "always-on
production database serving real users." Workspace guidance (§25 of the batch that produced this
project, and the workspace cost-runaway playbook) explicitly requires this tradeoff to be a
disclosed ADR, not a silently-adopted shortcut presented as the production design.

## Decision

The **public demo deployment** runs PostgreSQL/pgvector as a container *inside* the same Azure
Container Apps Environment as the application, with **ephemeral, non-persistent storage**. On
every cold start, the app runs `init-db` + `ingest data/sample` automatically before serving
traffic, so the demo is always populated with the sample knowledge base — at the cost of any
demo-time-only data (e.g. someone ingesting their own test document through a future upload
feature) not surviving a restart.

**This is explicitly not the production-recommended architecture.** A production deployment of
this project would use Azure Database for PostgreSQL Flexible Server (managed, backed up,
point-in-time restore, HA) exactly as `deploy/local/docker-compose.yml` already models for local
dev with a real (if smaller-scale) Postgres. The demo tradeoff exists purely for public-portfolio
cost reasons.

## Alternatives considered

- **Managed Azure Database for PostgreSQL for the demo too**: rejected for the *demo specifically*
  — recurring cost with no corresponding benefit, since the demo's data is fully reproducible
  sample content, not anything that needs durability guarantees.
- **No database at all, in-memory vector store for the demo**: rejected — would mean the demo
  runs meaningfully different code from what's actually being showcased (pgvector retrieval);
  defeats the purpose of a deployment proving the real architecture works.

## Consequences

- Demo data loss on restart is expected and harmless (sample data, re-seeded automatically).
- `docs/deployment.md` states this tradeoff explicitly so nobody mistakes the demo's persistence
  model for the production recommendation.
- Monthly cost stays near Azure Container Apps' consumption-based minimum (see
  `docs/deployment.md` for the estimate) rather than a fixed managed-database charge.

## Revisit conditions

If this project is ever deployed for real internal team use (not a portfolio demo), switch to
managed PostgreSQL immediately — this ADR's decision applies only to the public portfolio demo.
