"""Construcción del prompt para Bedrock y cálculo de deltas entre informes.

Separado del handler para poder testear esta lógica sin AWS de por
medio: es texto entrando, texto/dict saliendo.
"""

from __future__ import annotations

import json

PROMPT_INSTRUCTIONS = (
    "Eres un analista que ayuda a llevar un negocio de reventa de ropa "
    "vintage en Vinted. A partir de las métricas de inventario de abajo, "
    "escribe un resumen breve en español (máximo 150 palabras), en tono "
    "directo y práctico. Destaca lo más relevante: categorías con rotación "
    "baja, cambios notables respecto al informe anterior si los hay, y una "
    "sugerencia de acción concreta. No repitas todas las cifras, elige las "
    "que importan."
)


def compute_deltas(latest: dict, previous: dict | None) -> dict:
    """Compara sell_through_rate y avg_sale_price entre dos snapshots.

    Devuelve {} si no hay informe anterior o si ninguna categoría común
    tiene datos comparables.
    """
    if previous is None:
        return {}

    deltas: dict[str, dict[str, float]] = {}
    previous_categories = previous.get("by_category", {})

    for category, current in latest.get("by_category", {}).items():
        prior = previous_categories.get(category)
        if prior is None:
            continue

        delta: dict[str, float] = {}
        current_rate = current.get("sell_through_rate")
        prior_rate = prior.get("sell_through_rate")
        if current_rate is not None and prior_rate is not None:
            delta["sell_through_rate_change"] = round(current_rate - prior_rate, 4)

        current_price = current.get("avg_sale_price")
        prior_price = prior.get("avg_sale_price")
        if current_price is not None and prior_price is not None:
            delta["avg_sale_price_change"] = round(current_price - prior_price, 2)

        if delta:
            deltas[category] = delta

    return deltas


def build_prompt(latest: dict, deltas: dict, currency: str) -> str:
    """Arma el prompt que se envía a Bedrock a partir de métricas y deltas."""
    lines = [
        PROMPT_INSTRUCTIONS,
        "",
        f"Moneda: {currency}",
        f"Resumen global: {json.dumps(latest.get('overall', {}), ensure_ascii=False)}",
        f"Por categoría: {json.dumps(latest.get('by_category', {}), ensure_ascii=False)}",
    ]

    if deltas:
        lines.append(
            f"Cambios respecto al informe anterior: {json.dumps(deltas, ensure_ascii=False)}"
        )
    else:
        lines.append("No hay informe anterior con el que comparar (es el primer informe).")

    return "\n".join(lines)
