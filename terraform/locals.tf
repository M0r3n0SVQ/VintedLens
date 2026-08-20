locals {
  # Tags mínimas aplicadas a todos los recursos vía default_tags del
  # provider (ver providers.tf). Cualquier recurso que necesite tags
  # adicionales las añade con merge(local.common_tags, { ... }).
  common_tags = {
    project     = var.project
    environment = var.environment
    owner       = var.owner
  }

  processing_lambda_name      = "${var.project}-${var.environment}-processing"
  processing_parameter_prefix = "/${var.project}/${var.environment}/processing"
}

data "aws_caller_identity" "current" {}
