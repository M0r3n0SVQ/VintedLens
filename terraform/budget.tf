# Guardarraíl de coste: el objetivo declarado del proyecto es no pagar
# nada de AWS. El límite es deliberadamente bajo (1 USD) y la primera
# alerta salta al 1% de ese límite, es decir, en cuanto aparece
# CUALQUIER cargo real en la cuenta — no espera a acercarse al límite.
# Se complementa con una alerta de coste previsto (forecast) por si el
# ritmo de gasto del mes va camino de superar el límite.

resource "aws_budgets_budget" "zero_spend_guardrail" {
  name         = "${var.project}-${var.environment}-zero-spend"
  budget_type  = "COST"
  limit_amount = "1"
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 1
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.budget_alert_email]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.budget_alert_email]
  }
}
