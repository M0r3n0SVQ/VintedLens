variable "aws_region" {
  description = "Región de AWS donde se despliegan todos los recursos."
  type        = string
  default     = "eu-west-1"
}

variable "project" {
  description = "Nombre del proyecto, usado para nombrar y etiquetar recursos."
  type        = string
  default     = "vintedlens"
}

variable "environment" {
  description = "Entorno de despliegue (dev, prod, ...)."
  type        = string
  default     = "dev"
}

variable "owner" {
  description = "Responsable de los recursos, para etiquetado y trazabilidad."
  type        = string
  default     = "alvaro"
}

variable "budget_alert_email" {
  description = "Email que recibe las alertas de coste de AWS Budgets. Sin valor por defecto a propósito: se define en un terraform.tfvars local (no versionado) para no exponer un email personal en un repo público."
  type        = string
}
