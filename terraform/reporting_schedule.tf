# Disparo periódico del informe (no por cada CSV subido: el objetivo
# es un resumen cada cierto tiempo, no un email por archivo).

resource "aws_cloudwatch_event_rule" "reporting_schedule" {
  name                = "${var.project}-${var.environment}-reporting-schedule"
  description         = "Dispara el informe periódico de inventario."
  schedule_expression = var.report_schedule_expression
}

resource "aws_cloudwatch_event_target" "reporting_lambda" {
  rule      = aws_cloudwatch_event_rule.reporting_schedule.name
  target_id = "reporting-lambda"
  arn       = aws_lambda_function.reporting.arn
}

resource "aws_lambda_permission" "allow_eventbridge_reporting" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.reporting.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.reporting_schedule.arn
}
