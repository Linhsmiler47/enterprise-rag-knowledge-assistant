output "app_url" {
  value       = "https://${azurerm_container_app.app.ingress[0].fqdn}"
  description = "Public URL of the deployed application."
}

output "resource_group" {
  value = azurerm_resource_group.main.name
}
