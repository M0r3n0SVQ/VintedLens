# Lambda de reporting: resume las métricas más recientes con Bedrock
# y envía el resultado por email vía SES.
#
# SES en modo sandbox (el modo por defecto de una cuenta nueva) exige
# verificar tanto el remitente como el destinatario. Usamos el mismo
# email como ambos (el informe se lo manda uno mismo), así que basta
# con verificar una sola identidad y no hace falta pedir salir del
# sandbox — no tiene sentido para un único destinatario.

resource "aws_ses_email_identity" "report" {
  email = var.report_email
}

resource "aws_cloudwatch_log_group" "reporting_lambda" {
  name              = "/aws/lambda/${local.reporting_lambda_name}"
  retention_in_days = 14
}

resource "aws_iam_role" "reporting_lambda" {
  name               = local.reporting_lambda_name
  assume_role_policy = data.aws_iam_policy_document.processing_lambda_assume.json
}

# Permisos mínimos: listar/leer solo processed/*, invocar solo el
# modelo de Bedrock configurado, enviar email solo desde/hacia la
# identidad SES verificada de este proyecto, y logs.
data "aws_iam_policy_document" "reporting_lambda_permissions" {
  statement {
    sid       = "ListProcessedObjects"
    effect    = "Allow"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.data.arn]

    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values   = ["processed/*"]
    }
  }

  statement {
    sid       = "ReadProcessedObjects"
    effect    = "Allow"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.data.arn}/processed/*"]
  }

  statement {
    sid     = "ReadReportingConfig"
    effect  = "Allow"
    actions = ["ssm:GetParametersByPath", "ssm:GetParameter"]
    resources = [
      "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter${local.reporting_parameter_prefix}",
      "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter${local.reporting_parameter_prefix}/*",
    ]
  }

  statement {
    # Los modelos de Anthropic solo se invocan vía inference profile,
    # pero el profile enruta internamente a un foundation model real en
    # alguna región EU: IAM exige permiso sobre ambos recursos, no solo
    # el profile. El comodín de región cubre el conjunto de regiones EU
    # del profile sin tener que enumerarlas (y sin romper si AWS lo
    # cambia).
    sid     = "InvokeBedrockModel"
    effect  = "Allow"
    actions = ["bedrock:InvokeModel"]
    resources = [
      "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:inference-profile/${var.bedrock_model_id}",
      "arn:aws:bedrock:*::foundation-model/${local.bedrock_foundation_model_id}",
    ]
  }

  statement {
    sid       = "SendReportEmail"
    effect    = "Allow"
    actions   = ["ses:SendEmail", "ses:SendRawEmail"]
    resources = [aws_ses_email_identity.report.arn]
  }

  statement {
    sid    = "WriteLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["${aws_cloudwatch_log_group.reporting_lambda.arn}:*"]
  }
}

resource "aws_iam_role_policy" "reporting_lambda" {
  name   = local.reporting_lambda_name
  role   = aws_iam_role.reporting_lambda.id
  policy = data.aws_iam_policy_document.reporting_lambda_permissions.json
}

resource "aws_lambda_function" "reporting" {
  function_name    = local.reporting_lambda_name
  role             = aws_iam_role.reporting_lambda.arn
  handler          = "reporting.handler.handler"
  runtime          = "python3.12"
  timeout          = 60
  memory_size      = 256
  filename         = data.archive_file.lambda_src.output_path
  source_code_hash = data.archive_file.lambda_src.output_base64sha256

  environment {
    variables = {
      PROJECT      = var.project
      ENVIRONMENT  = var.environment
      DATA_BUCKET  = aws_s3_bucket.data.bucket
      REPORT_EMAIL = var.report_email
    }
  }

  depends_on = [aws_cloudwatch_log_group.reporting_lambda]
}
