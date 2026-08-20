# Bucket dedicado al estado remoto de Terraform, separado del bucket
# de datos: el estado puede contener valores sensibles (ARNs, IDs) y
# tiene un ciclo de vida y unos permisos distintos a los datos de
# negocio, así que no comparte bucket con ellos.
#
# Se crea con estado local (bootstrap); una vez existe, el backend
# "s3" en versions.tf apunta aquí y `terraform init -migrate-state`
# mueve el estado. No usa DynamoDB para el locking: desde Terraform
# 1.11 el backend S3 soporta locking nativo vía conditional writes
# (use_lockfile), así que una tabla DynamoDB solo para esto sería un
# recurso de más sin beneficio real.

resource "random_id" "tfstate_suffix" {
  byte_length = 4
}

resource "aws_s3_bucket" "tfstate" {
  bucket = "${var.project}-${var.environment}-tfstate-${random_id.tfstate_suffix.hex}"
}

resource "aws_s3_bucket_versioning" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
