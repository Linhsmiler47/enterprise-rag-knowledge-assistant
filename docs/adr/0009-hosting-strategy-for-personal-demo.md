# ADR-0009 — Hosting Strategy for a Personal, Low-Traffic Demo

**Status:** Proposed — awaiting explicit approval before any Azure resource is created or
`az login` is run (see `docs/deployment.md`'s "what has and hasn't been done" — nothing has been
deployed yet; this ADR only decides *what* would be deployed, not an authorization to deploy it).

## Context

ADR-0006 chose Azure Container Apps (ACA) as the deployment target for a generic "portfolio demo"
before the actual usage pattern was pinned down. The real requirement, stated explicitly for this
decision:

- A **personal** demo — not a shared/public always-on service.
- Traffic pattern: **a few test questions**, not sustained or unpredictable load.
- **Low cost** is a hard preference, ahead of production-grade resilience.
- **Mostly open-source runtime** preferred over Azure-managed services where the tradeoff is close.
- **No 24/7 public demo requirement yet** — availability doesn't need to be continuous.

This context changes the answer from ADR-0006's. ADR-0006 remains correct as *a* deployable
architecture (and is not deleted — the Terraform under `infra/environments/dev/` still targets
it); this ADR decides what to actually stand up first, given the real usage pattern above.

## Options compared

| | Current: ACA (app+db+ollama as Container Apps) | Azure VM + Docker Compose | ACA + managed PostgreSQL Flexible Server | Ephemeral deploy-only (apply before a demo, destroy after) |
|---|---|---|---|---|
| Reuses existing artifacts | Existing Terraform, as-is | Existing `docker-compose*.yml` almost unchanged; new (small) Terraform needed for the VM itself | Existing Terraform + a new managed-DB resource, app config changes | Existing Terraform, run on a manual schedule |
| Runtime "openness" | Azure Container Apps platform, self-hosted Postgres+Ollama containers | Plain Docker Compose on a Linux VM — same containers, no Azure-specific runtime | Azure Container Apps platform + Azure-managed Postgres (least open-source) | Same as current ACA option, just not always running |
| Always-on cost (if left running) | ~$20-30/mo (ADR-0007: `db` can't scale to zero without losing ephemeral data) | ~$25-35/mo for a 2 vCPU/4GB VM (enough headroom to run app+db+ollama concurrently) if left running 24/7 | ~$35-50+/mo (adds a managed Postgres Flexible Server on top of ACA app/ollama costs) | ~$0 when torn down |
| Cost if actually used only occasionally | Same as always-on — ACA's `db` can't be manually paused the way a VM can | **Near-$0**: `az vm deallocate` stops compute billing entirely; only the OS disk (~$1-3/mo) remains while stopped | Same as always-on — managed Postgres bills whether queried or not | ~$0, but requires re-running `terraform apply`/`destroy` (minutes) every time, plus re-seeding on every apply |
| Operational effort per demo session | None — always up | One `az vm start` / `az vm deallocate` (seconds) | None — always up | Full `terraform apply` + wait for provisioning + re-ingest, then `terraform destroy` — several minutes each way |
| New IaC work required | None — already written and validated | Small: one VM resource, NSG rule, a cloud-init script to install Docker + run the existing Compose files | Small-medium: a `azurerm_postgresql_flexible_server` resource + connection string wiring | None — reuses existing Terraform as-is |
| Fit for "24/7 not required yet" | Poor — pays the always-on `db` cost regardless of whether anyone visits | **Good** — cost tracks actual usage, not availability | Poor — same as current, plus a second always-on managed resource | Good on cost, poor on friction/readiness (nothing is up unless you remember to apply it first) |

## Decision

**Recommend: Azure VM + Docker Compose, started only for demo sessions and deallocated
otherwise.** This is a recommendation pending your approval, not an action taken.

Reasoning against the stated context:

- It's the only option whose **cost scales with actual usage** rather than uptime — `az vm
  deallocate` stops compute billing between test sessions, which directly serves "I will test
  only a few questions" + "I prefer low cost."
- It reuses `deploy/local/docker-compose.yml` + `docker-compose.ollama.yml` almost unchanged —
  the same app/db/ollama containers already validated locally, no Azure-managed database or
  Azure-specific container runtime in the loop. This is the most "open-source runtime" option of
  the four: Azure only supplies the VM, everything running on it is the project's own
  already-tested Docker stack.
- It's readier-on-demand than the ephemeral-apply option: `az vm start` (seconds, keeps the disk
  and container state as they were) vs. a full `terraform apply` + re-ingest cycle (minutes, from
  scratch) every time you want to show the demo.
- It does *not* require abandoning ADR-0006 — `infra/environments/dev/` (ACA) stays as the
  documented path to a real always-on deployment if/when 24/7 public availability actually becomes
  a requirement (this ADR's own revisit condition).

## Alternatives considered

- **Current ACA (ADR-0006), unchanged**: rejected as the *first* thing to stand up — it pays for
  an always-on ephemeral Postgres container regardless of whether the demo is being watched,
  which doesn't fit "I will test only a few questions." Kept as the documented path for a future
  always-on public demo.
- **ACA + managed PostgreSQL Flexible Server**: rejected — strictly more expensive and more
  Azure-managed-service-dependent than the current ACA option, with no benefit for a
  personal/low-traffic demo whose data is fully reproducible sample content (ADR-0007's reasoning
  applies even more strongly here).
- **Ephemeral deploy-only (apply/destroy per session)**: rejected as the *default*, not because
  it's a bad idea, but because it has higher per-session friction (full infrastructure
  provisioning + re-ingest each time) than a VM you can just start/stop, for the same near-zero
  cost-when-idle benefit. Worth reconsidering if even the VM's small idle disk cost matters, or if
  the demo will be shown so rarely that "provision from scratch" is genuinely fine.

## Consequences

- Requires **new Terraform** not yet written: a VM resource, network security group (scoped to
  the ports actually needed — SSH for the operator, HTTP for the demo — not open to all of
  `0.0.0.0/0` without thought), and a cloud-init/startup script that installs Docker and runs the
  existing Compose files. This is explicit follow-up work, gated on this ADR being approved, not
  bundled into this change.
- The existing `infra/environments/dev/` ACA Terraform is **not removed or modified** by this
  decision — it remains validated and available, just not the first thing deployed.
- Manual start/stop discipline is now a real operational responsibility (forgetting to deallocate
  defeats the entire cost rationale) — should be documented as an explicit runbook step once
  implemented.
- All cost figures above are rough list-price estimates in the same spirit as
  `docs/deployment.md`'s existing ACA estimate — not fetched from live Azure pricing in this
  change, and not a substitute for checking the Azure Cost Management dashboard after a real
  deployment.

## Revisit conditions

Move to the current ACA architecture (ADR-0006) — or ACA + managed PostgreSQL if durability
becomes a real requirement — once any of these becomes true: the demo needs to be reachable by
someone else without you manually starting a VM first, traffic becomes frequent/unpredictable
enough that manual start/stop is impractical, or 24/7 public availability becomes an actual
requirement rather than a "not yet."
