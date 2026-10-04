# Deployment

## Hosting strategy under review

[ADR-0009](adr/0009-hosting-strategy-for-personal-demo.md) proposes switching the *first* deployed
environment from the ACA topology below to an Azure VM + Docker Compose, started/deallocated on
demand, given this project's actual usage pattern (personal, low-traffic, no 24/7 requirement).
That ADR is **Proposed, not approved** — the topology below (already validated via
`terraform validate`, never deployed) remains the documented target until/unless ADR-0009 is
approved and new VM Terraform is written.

## Current Azure topology (ADR-0006, as currently written — see ADR-0009 for a proposed change)

```
                    GitHub Actions
                          │ OIDC (workload identity federation)
                          ▼
              Azure Resource Group (rg-enterprise-rag-knowledge-assistant-dev)
                          │
              Azure Container Apps Environment
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
  ca-...-app         ca-...-db          ca-...-ollama
  (FastAPI,          (pgvector,         (qwen2.5:0.5b +
   external           internal-only,     all-minilm,
   ingress,           ephemeral —        internal-only,
   scale 0-2)         ADR-0007)          scale-to-zero)
        │
        ▼
  Log Analytics Workspace (ACA default logs/metrics sink)
```

See [ADR-0006](adr/0006-azure-container-apps.md) (why Container Apps) and
[ADR-0007](adr/0007-demo-persistence-cost-tradeoff.md) (why ephemeral Postgres + self-hosted
Ollama instead of managed services for the demo specifically).

## IaC

`infra/environments/dev/` (Terraform, `azurerm` provider ~> 4.0). Validated locally
(`terraform init -backend=false && terraform validate` — passes). State backend: Azure Storage,
configured via `-backend-config` at `terraform init` time (not hardcoded — differs per
subscription), key `enterprise-rag-knowledge-assistant/dev.tfstate` per the workspace's
extraction-survives-unchanged convention.

```bash
cd infra/environments/dev
terraform init -backend-config=<path-to-backend-config>
terraform plan -var-file=dev.tfvars -var="image=..." -var="ghcr_username=..." -var="ghcr_token=..."
terraform apply -var-file=dev.tfvars ...
```

## Authentication

**Target (per the incubating workspace's ADR-0006 — see its `docs/adr/` if this project is still
incubating there):** GitHub Actions authenticates to Azure via OIDC / workload identity
federation — no long-lived Azure credential stored as a GitHub Secret.

**Current status: prepared, not completed.** Setting up the federated credential requires an
Azure AD app registration and role assignment, which requires an authenticated `az login`
(interactive browser or device-code flow) — that's a human action this cannot perform
autonomously in this environment. See `docs/playbooks/cloud-bootstrap-azure.md` (workspace root)
for the exact steps; `deploy.yml` is written to consume the federated credential once it exists
(`azure/login@v2` with `client-id`/`tenant-id`/`subscription-id`, no `client-secret`).

## Environment configuration

| Variable | Source |
|---|---|
| `DATABASE_URL` | Set by Terraform to the internal `db` container's address |
| `LLM_PROVIDER`, `LLM_BASE_URL` | Set by Terraform to point at the internal `ollama` container |
| `LLM_API_KEY` | ACA secret (Terraform variable, CI-supplied — not committed); irrelevant for the default Ollama path |
| `ghcr_username` / `ghcr_token` | CI secrets, used only for pulling the image from GHCR |

## Approximate cost (demo environment)

Azure Container Apps consumption pricing, `eastus`, as of this writing:

| Resource | Behavior | Rough monthly cost at demo traffic |
|---|---|---|
| `app` (scale 0-2, 0.5 vCPU/1Gi) | Scale-to-zero when idle | ~$0-3 |
| `db` (min replicas 1, 0.5 vCPU/1Gi) | Always-on (stateful-ish, ephemeral) | ~$15-20 |
| `ollama` (scale-to-zero, 1 vCPU/2Gi) | Scale-to-zero when idle | ~$0-2 |
| Log Analytics (30-day retention) | Pay-per-GB ingested | ~$1-3 at demo log volume |

**Estimated total: ~$20-30/month**, dominated by keeping `db` always-on (required because it
holds ephemeral data that a scale-to-zero restart would lose — see ADR-0007). A budget alert at
$8 (80% of the $10 Terraform-configured budget) is configured to catch runaway cost before it
becomes a surprise. These are estimates, not a substitute for watching the actual Azure Cost
Management dashboard after a real deployment.

## Teardown

```bash
cd infra/environments/dev
terraform destroy -var-file=dev.tfvars -var="image=..." -var="ghcr_username=..." -var="ghcr_token=..."
```

Removes the entire resource group and everything in it. See the workspace root
`docs/playbooks/incident-cost-runaway.md` for the emergency (partial, faster) version.

## What has and hasn't been done (honesty, not aspiration)

- ✅ Terraform written and locally validated (`terraform validate` passes)
- ✅ `deploy.yml` written with a manual-only trigger, targeting OIDC auth
- ❌ **Not deployed.** No `terraform apply` has been run. No Azure resources exist. `az login`
  requires interactive authentication this environment cannot perform — see "Authentication"
  above and the final batch report's "remaining manual actions" section.
