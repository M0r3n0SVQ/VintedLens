# API HTTP (API Gateway v2, más barato y simple que REST API) que
# expone las métricas más recientes al dashboard de la Fase 5. Sin
# CORS: la llamada la hace el servidor de Next.js, no el navegador,
# así la clave de la API nunca llega al cliente.

resource "random_password" "api_key" {
  length  = 40
  special = false
}

resource "aws_ssm_parameter" "api_key" {
  name  = local.api_key_parameter_name
  type  = "SecureString"
  value = random_password.api_key.result
}

data "aws_kms_alias" "ssm" {
  name = "alias/aws/ssm"
}

resource "aws_cloudwatch_log_group" "api_lambda" {
  name              = "/aws/lambda/${local.api_lambda_name}"
  retention_in_days = 14
}

resource "aws_iam_role" "api_lambda" {
  name               = local.api_lambda_name
  assume_role_policy = data.aws_iam_policy_document.processing_lambda_assume.json
}

# Permisos mínimos: listar/leer solo processed/*, leer y descifrar
# solo la clave de esta API, y logs.
data "aws_iam_policy_document" "api_lambda_permissions" {
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
    sid       = "ReadApiKey"
    effect    = "Allow"
    actions   = ["ssm:GetParameter"]
    resources = ["arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter${local.api_key_parameter_name}"]
  }

  statement {
    sid       = "DecryptApiKey"
    effect    = "Allow"
    actions   = ["kms:Decrypt"]
    resources = [data.aws_kms_alias.ssm.target_key_arn]
  }

  statement {
    sid    = "WriteLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["${aws_cloudwatch_log_group.api_lambda.arn}:*"]
  }
}

resource "aws_iam_role_policy" "api_lambda" {
  name   = local.api_lambda_name
  role   = aws_iam_role.api_lambda.id
  policy = data.aws_iam_policy_document.api_lambda_permissions.json
}

resource "aws_lambda_function" "api" {
  function_name    = local.api_lambda_name
  role             = aws_iam_role.api_lambda.arn
  handler          = "api.handler.handler"
  runtime          = "python3.12"
  timeout          = 15
  memory_size      = 256
  filename         = data.archive_file.lambda_src.output_path
  source_code_hash = data.archive_file.lambda_src.output_base64sha256

  environment {
    variables = {
      PROJECT     = var.project
      ENVIRONMENT = var.environment
      DATA_BUCKET = aws_s3_bucket.data.bucket
    }
  }

  depends_on = [aws_cloudwatch_log_group.api_lambda]
}

resource "aws_apigatewayv2_api" "api" {
  name          = local.api_gateway_name
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "api" {
  api_id                 = aws_apigatewayv2_api.api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.api.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "metrics" {
  api_id    = aws_apigatewayv2_api.api.id
  route_key = "GET /metrics"
  target    = "integrations/${aws_apigatewayv2_integration.api.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.api.id
  name        = "$default"
  auto_deploy = true

  # Sin límite, cualquiera podría probar la x-api-key a fuerza bruta
  # (o simplemente generar tráfico) sin ningún techo. 5 req/s con
  # ráfaga de 10 es de sobra para un dashboard de un solo usuario y
  # cierra esa puerta sin coste ni complejidad añadida.
  default_route_settings {
    throttling_rate_limit  = 5
    throttling_burst_limit = 10
  }
}

resource "aws_lambda_permission" "allow_apigateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.api.execution_arn}/*/*"
}
