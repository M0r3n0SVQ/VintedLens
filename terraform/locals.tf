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

  reporting_lambda_name      = "${var.project}-${var.environment}-reporting"
  reporting_parameter_prefix = "/${var.project}/${var.environment}/reporting"

  # Los modelos de Anthropic en Bedrock solo se pueden invocar a través
  # de un "inference profile" (bedrock_model_id, con prefijo de geografía
  # como "eu."), nunca con el ID del modelo base directamente. El ARN
  # del modelo base (sin el prefijo) también hace falta en la política
  # IAM: ver reporting.tf.
  bedrock_foundation_model_id = trimprefix(var.bedrock_model_id, "eu.")

  github_owner_name = split("/", var.github_repository)[0]
  github_repo_name  = split("/", var.github_repository)[1]
}

data "aws_caller_identity" "current" {}
