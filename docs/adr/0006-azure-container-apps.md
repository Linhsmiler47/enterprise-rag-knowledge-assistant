# ADR-0006 — Azure Container Apps as Deployment Target

**Status:** Accepted

## Context

Workspace [ADR-0004](../../../../docs/adr/0004-cloud-targets-azure-current-primary-aws-secondary.md)
sets Azure as the current primary cloud target; workspace
[ADR-0003](../../../../docs/adr/0003-containers-first-kubernetes-optional.md) sets containers-first,
Kubernetes-optional. This project needs one real compute target for its first cloud deployment,
kept cheap enough for a personal portfolio demo.

## Decision

Deploy to **Azure Container Apps** (ACA): a single Container App running the FastAPI image, in a
Container Apps Environment sized for demo traffic (not production scale). Not AKS — no Kubernetes
cluster to operate for a single-service demo.

## Alternatives considered

- **AKS**: rejected — a full Kubernetes cluster (even with a free control plane) is real
  operational and cost overhead for one container; workspace ADR-0003 already rejects this as the
  default.
- **App Service**: viable alternative, rejected in favor of ACA specifically because ACA's
  scale-to-zero behavior fits a portfolio demo's actual traffic pattern (near-zero most of the
  time) better than App Service's always-on plans.
- **Azure Functions**: rejected — this is a stateful, session-scoped FastAPI app with a
  persistent-ish process (DB connections, embedding client), not a natural fit for the
  functions-as-a-service execution model.

## Consequences

- Scale-to-zero means the first request after idle has cold-start latency — acceptable for a
  portfolio demo, would need addressing (min replicas ≥ 1) for a real production SLA.
- `infra/` targets exactly: resource group, Container Apps Environment, Container App(s), Key
  Vault (if secrets needed beyond OIDC-injected values), Log Analytics workspace (ACA's default
  logging sink) — see `infra/` and `docs/deployment.md`.

## Revisit conditions

If sustained traffic or a scaling pattern ACA can't handle well emerges, revisit — not before
there's a real reason.
