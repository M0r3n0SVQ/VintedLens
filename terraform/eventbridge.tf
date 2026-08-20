# raw/ -> EventBridge -> Lambda de procesamiento. La regla filtra por
# bucket y prefijo raw/ para no reaccionar a las propias escrituras en
# processed/ que hace la Lambda: eso evitaría cualquier posibilidad de
# bucle de recursión S3 -> Lambda -> S3 -> Lambda...

resource "aws_s3_bucket_notification" "data" {
  bucket      = aws_s3_bucket.data.id
  eventbridge = true
}

resource "aws_cloudwatch_event_rule" "raw_object_created" {
  name        = "${var.project}-${var.environment}-raw-object-created"
  description = "Dispara el procesamiento al subir un CSV a raw/ en el bucket de datos."

  event_pattern = jsonencode({
    source      = ["aws.s3"]
    detail-type = ["Object Created"]
    detail = {
      bucket = { name = [aws_s3_bucket.data.bucket] }
      object = { key = [{ prefix = "raw/" }] }
    }
  })

  depends_on = [aws_s3_bucket_notification.data]
}

resource "aws_cloudwatch_event_target" "processing_lambda" {
  rule      = aws_cloudwatch_event_rule.raw_object_created.name
  target_id = "processing-lambda"
  arn       = aws_lambda_function.processing.arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.processing.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.raw_object_created.arn
}
