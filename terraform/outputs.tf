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
