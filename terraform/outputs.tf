# Outputs del bucket de datos.
output "data_bucket_name" {
  description = "Nombre del bucket S3 que almacena los datos de inventario/ventas (raw/ y processed/)."
  value       = aws_s3_bucket.data.bucket
}

output "data_bucket_arn" {
  description = "ARN del bucket S3 que almacena los datos de inventario/ventas."
  value       = aws_s3_bucket.data.arn
}

output "tfstate_bucket_name" {
  description = "Nombre del bucket S3 que almacena el estado remoto de Terraform."
  value       = aws_s3_bucket.tfstate.bucket
}

output "processing_lambda_name" {
  description = "Nombre de la Lambda de procesamiento."
  value       = aws_lambda_function.processing.function_name
}

output "processing_lambda_arn" {
  description = "ARN de la Lambda de procesamiento."
  value       = aws_lambda_function.processing.arn
}

output "reporting_lambda_name" {
  description = "Nombre de la Lambda de reporting."
  value       = aws_lambda_function.reporting.function_name
}

output "report_email" {
  description = "Email del informe. AWS envía un correo de verificación a esta dirección al hacer apply; hay que confirmarlo antes de que SES pueda enviar el informe."
  value       = aws_ses_email_identity.report.email
}

output "github_actions_role_arn" {
  description = "ARN del rol que asumen los workflows de GitHub Actions vía OIDC. Se usa como AWS_ROLE_ARN (variable de repo, no secret) en la configuración de GitHub Actions."
  value       = aws_iam_role.github_actions.arn
}

output "api_endpoint" {
  description = "URL base de la API del dashboard. El endpoint de métricas es <api_endpoint>/metrics."
  value       = aws_apigatewayv2_stage.default.invoke_url
}

output "api_key" {
  description = "Clave para el header x-api-key. No se imprime por defecto: recupérala con `terraform output -raw api_key`."
  value       = random_password.api_key.result
  sensitive   = true
}
