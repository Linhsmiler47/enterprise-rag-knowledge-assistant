# Enterprise RAG Knowledge Assistant -- Azure Container Apps (dev/demo environment)
# See docs/deployment.md for the topology diagram and docs/adr/0006, docs/adr/0007 for why.
#
# Scope kept deliberately minimal: no unused multi-cloud modules, no resources this project
# doesn't actually use. Ollama runs as a container in the same environment so the demo needs
# zero paid API keys (NFR-001) -- see docs/adr/0007 for the cost/persistence tradeoff this
# implies (ephemeral Postgres, model re-pull on cold start).

locals {
  name_prefix = "${var.project_name}-${var.environment}"
  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "azurerm_resource_group" "main" {
  name     = "rg-${local.name_prefix}"
  location = var.location
  tags     = local.tags
}

resource "azurerm_log_analytics_workspace" "main" {
  name                = "log-${local.name_prefix}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "PerGB2018"
  retention_in_days   = 30 # minimum useful retention; keeps Log Analytics ingestion cost low
  tags                = local.tags
}

resource "azurerm_container_app_environment" "main" {
  name                       = "cae-${local.name_prefix}"
  resource_group_name        = azurerm_resource_group.main.name
  location                   = azurerm_resource_group.main.location
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
  tags                       = local.tags
}

# --- Database: PostgreSQL/pgvector as a container, ephemeral storage (ADR-0007) -------------
resource "azurerm_container_app" "db" {
  name                         = "ca-${local.name_prefix}-db"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"
  tags                         = local.tags

  template {
    min_replicas = 1 # stateful-ish; scale-to-zero would lose the ephemeral data on every idle
    max_replicas = 1

    container {
      name   = "db"
      image  = "pgvector/pgvector:pg16"
      cpu    = 0.5
      memory = "1Gi"

      env {
        name  = "POSTGRES_USER"
        value = "rag"
      }
      env {
        name  = "POSTGRES_PASSWORD"
        value = "rag" # demo-only, ephemeral, internal-only ingress -- see ADR-0007
      }
      env {
        name  = "POSTGRES_DB"
        value = "rag"
      }
    }
  }

  ingress {
    external_enabled = false
    target_port      = 5432
    transport        = "tcp"
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }
}

# --- Ollama: local-equivalent LLM/embeddings, no paid API key required (NFR-001) -------------
resource "azurerm_container_app" "ollama" {
  name                         = "ca-${local.name_prefix}-ollama"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"
  tags                         = local.tags

  template {
    min_replicas = 0 # scale-to-zero; first request after idle re-pulls models (documented tradeoff)
    max_replicas = 1

    container {
      name    = "ollama"
      image   = "ollama/ollama:latest"
      cpu     = 1.0
      memory  = "2Gi"
      command = ["/bin/sh", "-c"]
      args    = ["ollama serve & sleep 5 && ollama pull qwen2.5:0.5b && ollama pull all-minilm && wait"]
    }
  }

  ingress {
    external_enabled = false
    target_port      = 11434
    transport        = "tcp"
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }
}

# --- Application ------------------------------------------------------------------------------
resource "azurerm_container_app" "app" {
  name                         = "ca-${local.name_prefix}"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"
  tags                         = local.tags

  registry {
    server               = "ghcr.io"
    username             = var.ghcr_username
    password_secret_name = "ghcr-token"
  }

  secret {
    name  = "ghcr-token"
    value = var.ghcr_token
  }

  secret {
    name  = "llm-api-key"
    value = var.llm_api_key
  }

  template {
    min_replicas = 0 # scale-to-zero -- see ADR-0006
    max_replicas = 2

    container {
      name   = "app"
      image  = var.image
      cpu    = 0.5
      memory = "1Gi"

      env {
        name  = "DATABASE_URL"
        value = "postgresql+psycopg://rag:rag@${azurerm_container_app.db.name}:5432/rag"
      }
      env {
        name  = "LLM_PROVIDER"
        value = var.llm_provider
      }
      env {
        name  = "LLM_BASE_URL"
        value = "http://${azurerm_container_app.ollama.name}:11434/v1"
      }
      env {
        name        = "LLM_API_KEY"
        secret_name = "llm-api-key"
      }

      startup_probe {
        transport = "HTTP"
        path      = "/live"
        port      = 8000
      }
      readiness_probe {
        transport = "HTTP"
        path      = "/ready"
        port      = 8000
      }
      liveness_probe {
        transport = "HTTP"
        path      = "/live"
        port      = 8000
      }
    }
  }

  ingress {
    external_enabled = true
    target_port      = 8000
    transport        = "auto"
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }
}

# --- Cost guardrail (see docs/playbooks/incident-cost-runaway.md) ---------------------------
resource "azurerm_consumption_budget_resource_group" "main" {
  name              = "budget-${local.name_prefix}"
  resource_group_id = azurerm_resource_group.main.id

  amount     = 10
  time_grain = "Monthly"

  time_period {
    start_date = "2026-08-01T00:00:00Z"
  }

  notification {
    enabled        = true
    threshold      = 80.0
    operator       = "GreaterThan"
    threshold_type = "Actual"
    contact_emails = [] # set via tfvars -- left empty in committed config, no personal data
  }
}
