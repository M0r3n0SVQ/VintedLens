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

variable "report_email" {
  description = "Email que recibe (y desde el que se envía) el informe periódico de inventario. Sin valor por defecto por el mismo motivo que budget_alert_email."
  type        = string
}

variable "report_schedule_expression" {
  description = "Expresión de programación de EventBridge para el informe periódico."
  type        = string
  default     = "rate(7 days)"
}

variable "bedrock_model_id" {
  description = "ID del inference profile de Bedrock usado para el resumen en lenguaje natural. Los modelos de Anthropic en Bedrock no admiten invocación on-demand directa: hace falta el inference profile (prefijo de geografía, aquí 'eu.' para mantener el tráfico dentro de la UE), no el ID del modelo base."
  type        = string
  default     = "eu.anthropic.claude-haiku-4-5-20251001-v1:0"
}

variable "github_repository" {
  description = "Repositorio de GitHub (formato usuario/repo) autorizado a asumir el rol de GitHub Actions vía OIDC."
  type        = string
  default     = "M0r3n0SVQ/VintedLens"
}
