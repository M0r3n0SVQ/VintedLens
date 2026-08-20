# Lambda de procesamiento: limpia el CSV de raw/ y calcula métricas
# en processed/. Sin dependencias de terceros (solo boto3, incluido
# en el runtime), así que el paquete de despliegue es directamente el
# contenido de src/, sin paso de "pip install" previo (ver
# lambda_package.tf para el archive_file compartido).

resource "aws_cloudwatch_log_group" "processing_lambda" {
  name              = "/aws/lambda/${local.processing_lambda_name}"
  retention_in_days = 14
}

data "aws_iam_policy_document" "processing_lambda_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "processing_lambda" {
  name               = local.processing_lambda_name
  assume_role_policy = data.aws_iam_policy_document.processing_lambda_assume.json
}

# Permisos mínimos: leer solo raw/*, escribir solo processed/*, leer
# solo la configuración de este proyecto en Parameter Store, y logs.
data "aws_iam_policy_document" "processing_lambda_permissions" {
  statement {
    sid       = "ReadRawObjects"
    effect    = "Allow"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.data.arn}/raw/*"]
  }

  statement {
    sid       = "WriteProcessedObjects"
    effect    = "Allow"
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.data.arn}/processed/*"]
  }

  statement {
    # ssm:GetParametersByPath autoriza contra la ruta exacta que se pide
    # (sin /* al final); GetParameter autoriza contra cada parámetro
    # hijo. Hace falta el recurso exacto Y el comodín, no solo uno.
    sid     = "ReadProcessingConfig"
    effect  = "Allow"
    actions = ["ssm:GetParametersByPath", "ssm:GetParameter"]
    resources = [
      "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter${local.processing_parameter_prefix}",
      "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter${local.processing_parameter_prefix}/*",
    ]
  }

  statement {
    sid    = "WriteLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["${aws_cloudwatch_log_group.processing_lambda.arn}:*"]
  }
}

resource "aws_iam_role_policy" "processing_lambda" {
  name   = local.processing_lambda_name
  role   = aws_iam_role.processing_lambda.id
  policy = data.aws_iam_policy_document.processing_lambda_permissions.json
}

resource "aws_lambda_function" "processing" {
  function_name    = local.processing_lambda_name
  role             = aws_iam_role.processing_lambda.arn
  handler          = "processing.handler.handler"
  runtime          = "python3.12"
  timeout          = 30
  memory_size      = 256
  filename         = data.archive_file.lambda_src.output_path
  source_code_hash = data.archive_file.lambda_src.output_base64sha256

  environment {
    variables = {
      PROJECT     = var.project
      ENVIRONMENT = var.environment
    }
  }

  depends_on = [aws_cloudwatch_log_group.processing_lambda]
}
