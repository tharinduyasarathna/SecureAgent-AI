
locals {
  resource_prefix = "${var.project_name}-${var.environment}"

  common_tags = {
    Project     = "SecureAgent-AI"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

resource "azurerm_resource_group" "main" {
  name     = "rg-${local.resource_prefix}"
  location = var.location
  tags     = local.common_tags
}
