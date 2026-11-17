
variable "subscription_id" {
  description = "Azure subscription ID"
  type        = string
}

variable "project_name" {
  description = "Project resource naming prefix"
  type        = string
  default     = "secureagent-ai"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "prod"
}

variable "location" {
  description = "Azure deployment region"
  type        = string
  default     = "northeurope"
}
