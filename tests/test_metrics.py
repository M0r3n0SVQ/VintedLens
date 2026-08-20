from datetime import date

from processing.metrics import compute_all_metrics
from processing.parsing import InventoryItem


def _item(**overrides: object) -> InventoryItem:
    base = dict(
        item_id="LV-0001",
        title="Prenda de prueba",
        category="vaqueros",
        brand="levis",
        size="M",
        condition="bueno",
        cost_price=5.0,
        listing_price=20.0,
        sale_price=None,
        listed_date=date(2026, 1, 1),
        sold_date=None,
        status="listed",
        platform="vinted",
    )
    base.update(overrides)
    return InventoryItem(**base)  # type: ignore[arg-type]


def test_sell_through_rate_and_avg_days_to_sell() -> None:
    items = [
        _item(status="sold", sale_price=18.0, sold_date=date(2026, 1, 11)),  # 10 días
        _item(status="sold", sale_price=22.0, sold_date=date(2026, 1, 21)),  # 20 días
        _item(status="listed"),
    ]

    result = compute_all_metrics(items, low_sell_through_threshold=0.3)
    vaqueros = result["by_category"]["vaqueros"]

    assert vaqueros["sold_count"] == 2
    assert vaqueros["listed_count"] == 1
    assert vaqueros["avg_days_to_sell"] == 15.0
    assert vaqueros["avg_sale_price"] == 20.0
    assert vaqueros["sell_through_rate"] == round(2 / 3, 4)
    assert vaqueros["low_rotation"] is False


def test_low_rotation_flag_below_threshold() -> None:
    items = [_item(status="listed") for _ in range(9)] + [
        _item(status="sold", sale_price=20.0, sold_date=date(2026, 1, 11))
    ]

    result = compute_all_metrics(items, low_sell_through_threshold=0.5)
    vaqueros = result["by_category"]["vaqueros"]

    assert vaqueros["sell_through_rate"] == 0.1
    assert vaqueros["low_rotation"] is True


def test_removed_items_are_excluded_from_sell_through_denominator() -> None:
    items = [
        _item(status="removed"),
        _item(status="sold", sale_price=20.0, sold_date=date(2026, 1, 11)),
    ]

    result = compute_all_metrics(items, low_sell_through_threshold=0.3)
    vaqueros = result["by_category"]["vaqueros"]

    assert vaqueros["removed_count"] == 1
    assert vaqueros["sell_through_rate"] == 1.0


def test_empty_batch_has_none_metrics_not_errors() -> None:
    result = compute_all_metrics([], low_sell_through_threshold=0.3)

    assert result["overall"]["sell_through_rate"] is None
    assert result["overall"]["avg_days_to_sell"] is None
    assert result["by_category"] == {}
