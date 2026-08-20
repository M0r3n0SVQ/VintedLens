"""Cálculo de métricas de inventario: rotación, precio medio y tiempo en catálogo.

Definiciones:
  - precio medio: media de listing_price (y de sale_price sobre lo
    vendido) en la categoría.
  - tiempo en catálogo: media de (sold_date - listed_date) en días,
    solo sobre artículos vendidos.
  - rotación (sell-through rate): sold / (sold + listed + reserved).
    Se excluye "removed" del denominador porque un artículo retirado
    ya no compite por venderse; incluirlo penalizaría la rotación de
    categorías donde simplemente se despublican prendas por otros
    motivos (cambio de temporada, error de publicación, etc.).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import mean

from .parsing import InventoryItem


@dataclass(frozen=True)
class CategoryMetrics:
    category: str
    total_count: int
    sold_count: int
    listed_count: int
    reserved_count: int
    removed_count: int
    avg_listing_price: float | None
    avg_sale_price: float | None
    avg_days_to_sell: float | None
    sell_through_rate: float | None
    low_rotation: bool

    def to_dict(self) -> dict:
        return asdict(self)


def _avg(values: list[float]) -> float | None:
    return round(mean(values), 2) if values else None


def compute_category_metrics(
    category: str,
    items: list[InventoryItem],
    low_sell_through_threshold: float,
) -> CategoryMetrics:
    """Calcula las métricas de rotación/precio/tiempo para un grupo de items."""
    sold = [i for i in items if i.status == "sold"]
    listed = [i for i in items if i.status == "listed"]
    reserved = [i for i in items if i.status == "reserved"]
    removed = [i for i in items if i.status == "removed"]

    avg_listing_price = _avg([i.listing_price for i in items])
    avg_sale_price = _avg([i.sale_price for i in sold if i.sale_price is not None])

    days_to_sell = [
        float((i.sold_date - i.listed_date).days) for i in sold if i.sold_date is not None
    ]
    avg_days_to_sell = _avg(days_to_sell)

    denominator = len(sold) + len(listed) + len(reserved)
    sell_through_rate = round(len(sold) / denominator, 4) if denominator else None

    low_rotation = sell_through_rate is not None and sell_through_rate < low_sell_through_threshold

    return CategoryMetrics(
        category=category,
        total_count=len(items),
        sold_count=len(sold),
        listed_count=len(listed),
        reserved_count=len(reserved),
        removed_count=len(removed),
        avg_listing_price=avg_listing_price,
        avg_sale_price=avg_sale_price,
        avg_days_to_sell=avg_days_to_sell,
        sell_through_rate=sell_through_rate,
        low_rotation=low_rotation,
    )


def compute_all_metrics(items: list[InventoryItem], low_sell_through_threshold: float) -> dict:
    """Calcula métricas globales y por categoría para un batch de items."""
    categories = sorted({item.category for item in items})

    by_category = {
        category: compute_category_metrics(
            category,
            [item for item in items if item.category == category],
            low_sell_through_threshold,
        ).to_dict()
        for category in categories
    }

    overall = compute_category_metrics("overall", items, low_sell_through_threshold).to_dict()

    return {"overall": overall, "by_category": by_category}
