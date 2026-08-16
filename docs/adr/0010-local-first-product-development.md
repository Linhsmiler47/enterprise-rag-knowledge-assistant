# ADR-0010 — Local-First Product Development Before Cloud Release

**Status:** Accepted

## Context

ADR-0009 proposed Azure VM + Docker Compose as the first real cloud deployment, gated on explicit
approval. Since then, product scope grew: Phase 2 (this change) adds a UI, upload, and object
storage; later phases add multi-format ingestion and retrieval-quality work. Deploying to Azure
*now*, before that product surface stabilizes, would mean redeploying (and re-paying for) every
intermediate experiment rather than validating a real release candidate.

## Decision

Cloud deployment moves from "next milestone" to a **later, explicit release gate** (Phase 10 in
the project roadmap — see `docs/architecture.md`), not a fixed date. Until then:

- Local Docker Compose (`make dev`) and GitHub Actions CI are the only delivery gates.
- `deploy.yml` and the Terraform under `infra/environments/dev/` stay written and validated
  (`terraform validate`) but unexercised — no `az login`, no `terraform apply`, no Azure resources.
- Product features (UI, upload, storage, retrieval quality, guardrails, observability) are
  developed and evaluated entirely against the local stack.
- ADR-0009's analysis and recommendation (VM + Compose) remain valid content for when cloud
  deployment is actually approved — this ADR changes *when*, not *what*.

## Alternatives considered

- **Deploy an early demo now, iterate on it in place**: rejected — every Phase 2/3/4 change would
  either require redeploying (cost + operational overhead per iteration) or drifting the deployed
  version out of sync with local development, defeating the point of a "demo."
- **Deploy once Phase 2 (UI) ships, defer further**: rejected as a fixed rule — the same argument
  applies to Phase 3/4; the gate should be "is this a real release candidate," not "did we add a
  UI," which is why Phase 10 is framed as a business question (`docs/architecture.md`), not a
  version number.

## Consequences

- Portfolio evidence of cloud deployment capability is deferred — `docs/deployment.md` continues
  to state plainly that nothing is deployed, not implied readiness.
- All Phase 2+ evaluation, guardrail, and observability work must be verifiable locally
  (`make dev`, `make test`, `make ci`) — cloud-only validation paths are out of scope until Phase 10.
- CI must keep working without any cloud credential, matching NFR-001 and the existing `ci.yml`
  design — unaffected by this decision, just reaffirmed.

## Revisit conditions

Revisit once the product reaches a genuine release-candidate state (stable UI/upload workflow,
evaluation baseline extended past v0.1, guardrails hardened for the added attack surface) — at
that point, re-open ADR-0009 for fresh approval before any real Azure action, per its own terms.
