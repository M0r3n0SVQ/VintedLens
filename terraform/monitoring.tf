# Observabilidad mínima: hasta ahora la única alerta que existía era
# la de presupuesto (budget.tf), que avisa de gasto pero no de que
# algo se haya roto. Un fallo silencioso en processing o reporting no
# cuesta dinero, pero sí se nota (no llega el email, el dashboard se
# queda con datos viejos) — y sin esto no habría forma de enterarse
# sin mirar CloudWatch a mano.

resource "aws_sns_topic" "alerts" {
  name = "${var.project}-${var.environment}-alerts"
}

# La suscripción por email requiere confirmación manual: tras el
# primer `terraform apply` llega un correo de AWS a esta dirección
# con un enlace de confirmación (igual que con la identidad SES de
# reporting.tf). Sin confirmarlo, las alarmas no notifican a nadie.
resource "aws_sns_topic_subscription" "alerts_email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.budget_alert_email
}

# Una alarma por Lambda en vez de una sola agregada: así el email de
# alerta ya dice qué función falló, sin tener que ir a mirar logs
# para saber por dónde empezar.
resource "aws_cloudwatch_metric_alarm" "processing_errors" {
  alarm_name          = "${local.processing_lambda_name}-errors"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 1
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.processing.function_name
  }

  alarm_description = "La Lambda de procesamiento ha fallado al menos una vez en los últimos 5 minutos."
  alarm_actions     = [aws_sns_topic.alerts.arn]
  ok_actions        = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "reporting_errors" {
  alarm_name          = "${local.reporting_lambda_name}-errors"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 1
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.reporting.function_name
  }

  alarm_description = "La Lambda de reporting (Bedrock + SES) ha fallado al menos una vez en los últimos 5 minutos."
  alarm_actions     = [aws_sns_topic.alerts.arn]
  ok_actions        = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "api_errors" {
  alarm_name          = "${local.api_lambda_name}-errors"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 1
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.api.function_name
  }

  alarm_description = "La Lambda de la API del dashboard ha fallado al menos una vez en los últimos 5 minutos."
  alarm_actions     = [aws_sns_topic.alerts.arn]
  ok_actions        = [aws_sns_topic.alerts.arn]
}
