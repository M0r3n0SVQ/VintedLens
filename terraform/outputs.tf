output "data_bucket_name" {
  description = "Nombre del bucket S3 que almacena los datos de inventario/ventas (raw/ y processed/)."
  value       = aws_s3_bucket.data.bucket
}

output "data_bucket_arn" {
  description = "ARN del bucket S3 que almacena los datos de inventario/ventas."
  value       = aws_s3_bucket.data.arn
}
