# ADR-0001 — Initial Architecture

**Status:** Accepted

## Context

This project starts from the workspace's canonical Python service template. At creation time,
there is no real product complexity yet to justify a database, message broker, cloud deployment,
or any advanced capability — only a runnable, testable, CI-ready service skeleton.

## Decision

**Start minimal, design for extension.** The initial architecture is a single FastAPI service
with:

- one configuration boundary (`src/enterprise_rag_knowledge_assistant/config.py`);
- three health endpoints (`/live`, `/ready`, `/health`);
- no database, no message broker, no cloud dependency;
- Docker + local Compose for local running;
- GitHub Actions `ci.yml` + `security.yml` as the only workflows.

Every future capability (database, event-driven ingestion, cloud deployment, Kubernetes,
observability, MCP/A2A, etc.) is added only when this project's actual, current requirements
justify it — each such addition should get its own ADR explaining why.

## Alternatives considered

- **Start with a fuller stack** (database, IaC, Kubernetes, monitoring pre-wired): rejected — this
  is the exact template-inflation pattern that "start minimal, design for extension" exists to
  avoid. An unused database or Terraform directory adds nothing before the product needs one.
- **No structure at all, fully ad hoc**: rejected — the Makefile contract, config boundary, and
  health-endpoint pattern are cheap to keep and pay off immediately (CI, portability, debugging).

## Consequences

- Adding a real capability later means actually adding it — there's no placeholder to fill in,
  which is intentional friction against speculative complexity.
- This project can be extracted to a standalone repository at any point without leaving behind
  unused infrastructure that only made sense inside the incubation workspace.

## Revisit conditions

Revisit this ADR (not by editing it — by adding a new one) whenever a real capability is added:
record the new decision, the alternatives considered, and why the minimal starting point no
longer covers the actual requirement.
