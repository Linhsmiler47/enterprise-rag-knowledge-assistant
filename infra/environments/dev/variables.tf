variable "project_name" {
  type    = string
  default = "enterprise-rag-knowledge-assistant"
}

variable "environment" {
  type    = string
  default = "dev"
}

variable "location" {
  type        = string
  default     = "eastus"
  description = "Azure region. eastus chosen for broad Container Apps availability."
}

variable "image" {
  type        = string
  description = "Full image reference including registry, e.g. ghcr.io/<owner>/enterprise-rag-knowledge-assistant:sha-<digest>"
}

variable "ghcr_username" {
  type      = string
  sensitive = true
}

variable "ghcr_token" {
  type        = string
  sensitive   = true
  description = "GHCR read token (PAT with read:packages) -- passed via CI secret, never committed."
}

variable "llm_api_key" {
  type        = string
  sensitive   = true
  default     = "ollama"
  description = "Only meaningful when LLM_PROVIDER=openai; ignored by Ollama. Default keeps the demo on the free local-equivalent provider path -- see ADR-0002 in the app repo."
}

variable "llm_provider" {
  type    = string
  default = "ollama"
}
