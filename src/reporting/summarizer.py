"""Construcción del prompt para Bedrock y cálculo de deltas entre informes.

Separado del handler para poder testear esta lógica sin AWS de por
medio: es texto entrando, texto/dict saliendo.
"""

from __future__ import annotations

import json
import re

MAX_ITEM_SUGGESTIONS = 8

PROMPT_INSTRUCTIONS = (
    "Eres un analista que ayuda a llevar un negocio de reventa de ropa "
    "vintage en Vinted. A partir de las métricas de inventario y los "
    "artículos concretos de abajo, responde ÚNICAMENTE con un objeto "
    "JSON (sin markdown, sin texto fuera del JSON) con esta forma "
    "exacta:\n"
    '{"summary": "resumen breve en español, máximo 150 palabras, tono '
    "directo y práctico, destacando lo más relevante: categorías con "
    "rotación baja, cambios notables respecto al informe anterior si "
    'los hay. No repitas todas las cifras, elige las que importan.", '
    '"suggestions": [{"item_id": "...", "title": "el título tal cual '
    'aparece en los datos", "suggestion": "una mejora concreta para '
    "ESE artículo — precio, qué falta o sobra en el título/palabras "
    "de búsqueda, o fotos/estado. Basa la sugerencia en el título "
    "real: si ya incluye marca/talla/estado, no le digas que los "
    'añada, sugiere otra cosa"}]}\n'
    "Cada entrada de suggestions es sobre UN artículo de la lista de "
    "abajo, no sobre una categoría entera. Máximo una sugerencia por "
    "artículo de los listados. Si la lista de artículos está vacía, "
    "suggestions debe ser una lista vacía. Sé conciso (máximo 2 "
    "frases por sugerencia) para no quedarte sin espacio de respuesta."
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


def select_items_for_suggestions(
    items: list[dict], by_category: dict, limit: int = MAX_ITEM_SUGGESTIONS
) -> list[dict]:
    """Elige qué artículos concretos le pasamos a Bedrock para sugerencias.

    Solo artículos todavía listados (vendidos/reservados/retirados ya
    no necesitan una sugerencia de venta) en categorías marcadas como
    rotación baja. Se acota a `limit` para que el prompt no crezca sin
    límite con catálogos grandes: prioriza por precio de listado
    descendente, ya que ahí hay más capital inmovilizado.
    """
    low_rotation_categories = {
        category for category, metrics in by_category.items() if metrics.get("low_rotation")
    }

    candidates = [
        item
        for item in items
        if item.get("status") == "listed" and item.get("category") in low_rotation_categories
    ]

    candidates.sort(key=lambda item: item.get("listing_price") or 0, reverse=True)
    return candidates[:limit]


def build_prompt(latest: dict, deltas: dict, currency: str, items: list[dict]) -> str:
    """Arma el prompt que se envía a Bedrock a partir de métricas, deltas y artículos."""
    item_fields = ("item_id", "title", "category", "brand", "size", "condition", "listing_price")
    items_payload = [{field: item.get(field) for field in item_fields} for item in items]

    lines = [
        PROMPT_INSTRUCTIONS,
        "",
        f"Moneda: {currency}",
        f"Resumen global: {json.dumps(latest.get('overall', {}), ensure_ascii=False)}",
        f"Por categoría: {json.dumps(latest.get('by_category', {}), ensure_ascii=False)}",
        f"Artículos para sugerencias individuales: {json.dumps(items_payload, ensure_ascii=False)}",
    ]

    if deltas:
        lines.append(
            f"Cambios respecto al informe anterior: {json.dumps(deltas, ensure_ascii=False)}"
        )
    else:
        lines.append("No hay informe anterior con el que comparar (es el primer informe).")

    return "\n".join(lines)
