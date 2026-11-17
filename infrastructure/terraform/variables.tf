
variable "subscription_id" {
  description = "Azure subscription ID."
  type        = string
  sensitive   = true
}

variable "project_name" {
  description = "Name of the project."
  type        = string
  default     = "secureagent-ai"
}

variable "environment" {
  description = "Deployment environment."
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "location" {
  description = "Azure region."
  type        = string
  default     = "northeurope"
}

variable "tags" {
  description = "Additional Azure resource tags."
  type        = map(string)

  default = {
    Project   = "SecureAgent-AI"
    ManagedBy = "Terraform"
  }
}

variable "deploy_api" {
  description = "Whether to deploy the FastAPI Container App."
  type        = bool
  default     = false
}

variable "api_image" {
  description = "Container image for the FastAPI backend."
  type        = string
  default     = "mcr.microsoft.com/azuredocs/containerapps-helloworld:latest"
}

variable "api_cpu" {
  description = "CPU allocation for the FastAPI container."
  type        = number
  default     = 0.5
}

variable "api_memory" {
  description = "Memory allocation for the FastAPI container."
  type        = string
  default     = "1Gi"
}

variable "api_target_port" {
  description = "Port exposed by the FastAPI container."
  type        = number
  default     = 8000
}

variable "api_min_replicas" {
  description = "Minimum number of API replicas."
  type        = number
  default     = 0
}

variable "api_max_replicas" {
  description = "Maximum number of API replicas."
  type        = number
  default     = 1
}
