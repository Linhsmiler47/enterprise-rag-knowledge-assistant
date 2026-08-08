# Non-secret, reproducible environment values -- safe and intended to be committed.
# Secrets (ghcr_token, llm_api_key if using a real provider) are passed via
# `-var` / TF_VAR_* from CI, never written here. See docs/conventions/secrets.md.

project_name = "enterprise-rag-knowledge-assistant"
environment  = "dev"
location     = "eastus"
llm_provider = "ollama"
