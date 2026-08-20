# Paquete de código compartido por todas las Lambdas del proyecto.
# Se zipea src/ entero: cada función solo invoca su propio paquete
# (processing.handler.handler, reporting.handler.handler), el resto
# del código va de más en el zip pero no se ejecuta ni se importa. Es
# más simple que mantener un archive_file por Lambda y a este tamaño
# de código no hay coste real en zippear de más.

data "archive_file" "lambda_src" {
  type        = "zip"
  source_dir  = "${path.module}/../src"
  output_path = "${path.module}/.build/lambda_src.zip"
  excludes    = ["**/__pycache__/**", "**/*.pyc"]
}
