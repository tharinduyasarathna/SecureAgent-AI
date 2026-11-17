
output "resource_group_name" {
  description = "Azure resource group name"
  value       = azurerm_resource_group.main.name
}

output "resource_group_location" {
  description = "Azure deployment region"
  value       = azurerm_resource_group.main.location
}
