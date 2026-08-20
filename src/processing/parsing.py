"""Parsing y validación del CSV de inventario contra el esquema de VintedLens.

El contrato de columnas, enums y reglas vive en data/schema.md; este
módulo es la implementación de esa especificación, no una copia libre
de ella.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date

CATEGORIES = frozenset(
    {
        "vaqueros",
        "camisetas",
        "polos",
        "camisas",
        "chaquetas",
        "vestidos",
        "jerseys",
        "faldas",
        "pantalones",
        "calzado",
        "accesorios",
        "otros",
    }
)

CONDITIONS = frozenset(
    {
        "nuevo_con_etiquetas",
        "nuevo_sin_etiquetas",
        "muy_bueno",
        "bueno",
        "satisfactorio",
    }
)

STATUSES = frozenset({"listed", "reserved", "sold", "removed"})

REQUIRED_FIELDS = (
    "item_id",
    "title",
    "category",
    "condition",
    "cost_price",
    "listing_price",
    "listed_date",
    "status",
    "platform",
)


@dataclass(frozen=True)
class RowError:
    """Fila del CSV que no cumple el esquema y se descarta del batch."""

    row_number: int
    item_id: str
    reason: str


@dataclass(frozen=True)
class InventoryItem:
    """Una fila válida del CSV, ya parseada a tipos nativos."""

    item_id: str
    title: str
    category: str
    brand: str
    size: str
    condition: str
    cost_price: float
    listing_price: float
    sale_price: float | None
    listed_date: date
    sold_date: date | None
    status: str
    platform: str


def _parse_price(value: str) -> float:
    price = float(value)
    if price < 0:
        raise ValueError("el precio no puede ser negativo")
    return price


def parse_row(row: dict[str, str], row_number: int) -> InventoryItem:
    """Parsea y valida una fila del CSV.

    Raises:
        ValueError: si la fila incumple el contrato de data/schema.md.
    """
    for field in REQUIRED_FIELDS:
        if not (row.get(field) or "").strip():
            raise ValueError(f"falta el campo obligatorio '{field}'")

    category = row["category"].strip()
    if category not in CATEGORIES:
        raise ValueError(f"category '{category}' no reconocida")

    condition = row["condition"].strip()
    if condition not in CONDITIONS:
        raise ValueError(f"condition '{condition}' no reconocida")

    status = row["status"].strip()
    if status not in STATUSES:
        raise ValueError(f"status '{status}' no reconocido")

    cost_price = _parse_price(row["cost_price"])
    listing_price = _parse_price(row["listing_price"])

    sale_price_raw = (row.get("sale_price") or "").strip()
    sale_price = _parse_price(sale_price_raw) if sale_price_raw else None

    listed_date = date.fromisoformat(row["listed_date"].strip())

    sold_date_raw = (row.get("sold_date") or "").strip()
    sold_date = date.fromisoformat(sold_date_raw) if sold_date_raw else None

    if status == "sold" and (sale_price is None or sold_date is None):
        raise ValueError("status 'sold' requiere sale_price y sold_date")

    if sold_date is not None and sold_date < listed_date:
        raise ValueError("sold_date es anterior a listed_date")

    return InventoryItem(
        item_id=row["item_id"].strip(),
        title=row["title"].strip(),
        category=category,
        brand=(row.get("brand") or "desconocida").strip() or "desconocida",
        size=(row.get("size") or "").strip(),
        condition=condition,
        cost_price=cost_price,
        listing_price=listing_price,
        sale_price=sale_price,
        listed_date=listed_date,
        sold_date=sold_date,
        status=status,
        platform=row["platform"].strip(),
    )


def parse_csv(csv_text: str) -> tuple[list[InventoryItem], list[RowError]]:
    """Parsea un CSV completo, separando filas válidas de filas con error.

    Una fila inválida no aborta el resto del batch: se recoge en
    row_errors para que quede trazado en la salida, no silenciado.
    """
    reader = csv.DictReader(io.StringIO(csv_text))
    items: list[InventoryItem] = []
    errors: list[RowError] = []

    for row_number, row in enumerate(reader, start=2):  # la cabecera es la fila 1
        item_id = (row.get("item_id") or "").strip() or "<sin item_id>"
        try:
            items.append(parse_row(row, row_number))
        except ValueError as exc:
            errors.append(RowError(row_number=row_number, item_id=item_id, reason=str(exc)))

    return items, errors
