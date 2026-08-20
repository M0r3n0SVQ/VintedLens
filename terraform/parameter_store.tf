# Configuración de la Lambda de procesamiento. Tier estándar (gratis,
# sin límite de parámetros relevante a esta escala). Vive fuera del
# código para poder ajustar el umbral de rotación baja sin
# redesplegar la Lambda.

resource "aws_ssm_parameter" "raw_prefix" {
  name  = "${local.processing_parameter_prefix}/raw_prefix"
  type  = "String"
  value = "raw/"
}

resource "aws_ssm_parameter" "processed_prefix" {
  name  = "${local.processing_parameter_prefix}/processed_prefix"
  type  = "String"
  value = "processed/"
}

resource "aws_ssm_parameter" "low_sell_through_threshold" {
  name  = "${local.processing_parameter_prefix}/low_sell_through_threshold"
  type  = "String"
  value = "0.3"
}

resource "aws_ssm_parameter" "currency" {
  name  = "${local.processing_parameter_prefix}/currency"
  type  = "String"
  value = "EUR"
}
