
# ============================================================
# SecureAgent AI - Azure Infrastructure
# ============================================================

locals {
  resource_prefix = "${var.project_name}-${var.environment}"

  common_tags = merge(
    var.tags,
    {
      Environment = var.environment
    }
  )
}

# ============================================================
# Random suffix for globally unique Azure resources
# ============================================================

resource "random_string" "suffix" {
  length  = 6
  upper   = false
  special = false
}

# ============================================================
# Azure Resource Group
# ============================================================

resource "azurerm_resource_group" "main" {
  name     = "rg-${local.resource_prefix}"
  location = var.location

  tags = local.common_tags
}

# ============================================================
# Azure Container Registry
# ============================================================

resource "azurerm_container_registry" "main" {
  name = "acrsecureagent${random_string.suffix.result}"

  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location

  sku           = "Basic"
  admin_enabled = false

  tags = local.common_tags
}

# ============================================================
# Log Analytics Workspace
# ============================================================

resource "azurerm_log_analytics_workspace" "main" {
  name = "log-${local.resource_prefix}"

  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location

  sku               = "PerGB2018"
  retention_in_days = 30

  tags = local.common_tags
}

# ============================================================
# Azure Container Apps Environment
# ============================================================

resource "azurerm_container_app_environment" "main" {
  name = "cae-${local.resource_prefix}"

  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location

  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id

  tags = local.common_tags
}

# ============================================================
# Optional FastAPI Container App
#
# Disabled by default.
# Enable only after configuring a working image.
# ============================================================

resource "azurerm_container_app" "api" {
  count = var.deploy_api ? 1 : 0

  name = "ca-${local.resource_prefix}-api"

  resource_group_name          = azurerm_resource_group.main.name
  container_app_environment_id = azurerm_container_app_environment.main.id

  revision_mode = "Single"

  template {
    min_replicas = var.api_min_replicas
    max_replicas = var.api_max_replicas

    container {
      name   = "secureagent-api"
      image  = var.api_image
      cpu    = var.api_cpu
      memory = var.api_memory
    }
  }

  ingress {
    external_enabled = true
    target_port      = var.api_target_port

    transport = "auto"

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  tags = local.common_tags
}
