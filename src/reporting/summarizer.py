"""Construcción del prompt para Bedrock y cálculo de deltas entre informes.

Separado del handler para poder testear esta lógica sin AWS de por
medio: es texto entrando, texto/dict saliendo.
"""

from __future__ import annotations

import json
import re

PROMPT_INSTRUCTIONS = (
    "Eres un analista que ayuda a llevar un negocio de reventa de ropa "
    "vintage en Vinted. A partir de las métricas de inventario de abajo, "
    "responde ÚNICAMENTE con un objeto JSON (sin markdown, sin texto "
    "fuera del JSON) con esta forma exacta:\n"
    '{"summary": "resumen breve en español, máximo 150 palabras, tono '
    "directo y práctico, destacando lo más relevante: categorías con "
    "rotación baja, cambios notables respecto al informe anterior si "
    'los hay. No repitas todas las cifras, elige las que importan.", '
    '"suggestions": [{"category": "...", "suggestion": "una acción '
    "concreta y accionable para vender más rápido en esa categoría: "
    "precio, título/palabras clave de búsqueda, o estado/fotos — no "
    'genérica"}]}\n'
    "Incluye una entrada en suggestions solo por categorías marcadas "
    "como rotación baja en los datos, como máximo 5 — si hay más de 5, "
    "elige las de mayor volumen de stock sin vender. Si no hay ninguna "
    "categoría con rotación baja, suggestions debe ser una lista vacía. "
    "Sé conciso en cada sugerencia (máximo 2 frases) para no quedarte "
    "sin espacio de respuesta."
)


def parse_summary_response(raw_text: str) -> dict:
    """Parsea la respuesta de Bedrock (JSON esperado) en summary + suggestions.

    Bedrock a veces envuelve el JSON en un bloque ```json ... ``` pese a
    la instrucción de no hacerlo; se limpia antes de parsear. Si el
    parseo falla, se trata el texto completo como el resumen y no se
    aborta el informe por un JSON mal formado.
    """
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_text.strip())

    try:
        parsed = json.loads(cleaned)
        return {
            "summary": parsed.get("summary", raw_text),
            "suggestions": parsed.get("suggestions", []),
        }
    except (json.JSONDecodeError, AttributeError):
        return {"summary": raw_text, "suggestions": []}


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
