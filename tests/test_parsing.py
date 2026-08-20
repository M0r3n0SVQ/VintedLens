import pytest

from processing.parsing import parse_csv, parse_row


def _base_row(**overrides: str) -> dict[str, str]:
    row = {
        "item_id": "LV-9999",
        "title": "Prenda de prueba",
        "category": "otros",
        "condition": "bueno",
        "cost_price": "1",
        "listing_price": "2",
        "sale_price": "",
        "listed_date": "2026-01-01",
        "sold_date": "",
        "status": "listed",
        "platform": "vinted",
    }
    row.update(overrides)
    return row


def test_parse_csv_sample_all_valid(sample_csv_text: str) -> None:
    items, errors = parse_csv(sample_csv_text)
    assert len(items) == 8
    assert errors == []


def test_parse_row_rejects_unknown_category() -> None:
    with pytest.raises(ValueError, match="category"):
        parse_row(_base_row(category="sombreros"), row_number=2)


def test_parse_row_rejects_unknown_status() -> None:
    with pytest.raises(ValueError, match="status"):
        parse_row(_base_row(status="vendido"), row_number=2)


def test_parse_row_requires_sale_price_and_sold_date_when_sold() -> None:
    with pytest.raises(ValueError, match="sold"):
        parse_row(_base_row(status="sold", sold_date="2026-01-05"), row_number=2)


def test_parse_row_rejects_sold_date_before_listed_date() -> None:
    with pytest.raises(ValueError, match="anterior"):
        parse_row(
            _base_row(
                status="sold",
                sale_price="5",
                listed_date="2026-01-10",
                sold_date="2026-01-05",
            ),
            row_number=2,
        )


def test_parse_row_rejects_negative_price() -> None:
    with pytest.raises(ValueError, match="negativo"):
        parse_row(_base_row(cost_price="-1"), row_number=2)


def test_parse_row_defaults_missing_brand_to_desconocida() -> None:
    item = parse_row(_base_row(brand=""), row_number=2)
    assert item.brand == "desconocida"


def test_parse_csv_collects_row_errors_without_aborting_batch() -> None:
    csv_text = (
        "item_id,title,category,brand,size,condition,cost_price,listing_price,"
        "sale_price,listed_date,sold_date,status,platform\n"
        "LV-0001,Vaqueros ok,vaqueros,levis,M,bueno,5,20,,2026-01-01,,listed,vinted\n"
        "LV-0002,Categoria mala,sombreros,desconocida,M,bueno,5,20,,2026-01-01,,listed,vinted\n"
    )

    items, errors = parse_csv(csv_text)

    assert len(items) == 1
    assert items[0].item_id == "LV-0001"
    assert len(errors) == 1
    assert errors[0].item_id == "LV-0002"
    assert errors[0].row_number == 3
