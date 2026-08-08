terraform {
  required_version = ">= 1.9"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }

  # Remote state: created once, out-of-band, per the workspace's cloud-bootstrap playbook.
  # State key convention (survives extraction unchanged):
  #   enterprise-rag-knowledge-assistant/dev.tfstate
  backend "azurerm" {
    # resource_group_name, storage_account_name, container_name, key -- supplied via
    # `terraform init -backend-config=...` (not committed; differs per Azure subscription).
  }
}

provider "azurerm" {
  features {}
}
