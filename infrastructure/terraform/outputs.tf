
output "resource_group_name" {
  description = "Azure Resource Group name."
  value       = azurerm_resource_group.main.name
}

output "resource_group_location" {
  description = "Azure deployment region."
  value       = azurerm_resource_group.main.location
}

output "container_registry_name" {
  description = "Azure Container Registry name."
  value       = azurerm_container_registry.main.name
}

output "container_registry_login_server" {
  description = "Azure Container Registry login server."
  value       = azurerm_container_registry.main.login_server
}

output "log_analytics_workspace_id" {
  description = "Log Analytics Workspace resource ID."
  value       = azurerm_log_analytics_workspace.main.id
}

output "container_app_environment_id" {
  description = "Azure Container Apps Environment resource ID."
  value       = azurerm_container_app_environment.main.id
}

output "api_url" {
  description = "FastAPI public URL when API deployment is enabled."

  value = var.deploy_api ? (
    "https://${azurerm_container_app.api[0].ingress[0].fqdn}"
  ) : null
}
