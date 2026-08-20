from reporting.summarizer import build_prompt, compute_deltas


def _metrics(overall: dict, by_category: dict) -> dict:
    return {"overall": overall, "by_category": by_category}


def test_compute_deltas_returns_empty_without_previous() -> None:
    latest = _metrics({}, {"vaqueros": {"sell_through_rate": 0.5, "avg_sale_price": 20.0}})
    assert compute_deltas(latest, None) == {}


def test_compute_deltas_computes_change_for_shared_categories() -> None:
    latest = _metrics(
        {}, {"vaqueros": {"sell_through_rate": 0.5, "avg_sale_price": 20.0, "total_count": 5}}
    )
    previous = _metrics(
        {}, {"vaqueros": {"sell_through_rate": 0.65, "avg_sale_price": 22.0, "total_count": 4}}
    )

    deltas = compute_deltas(latest, previous)

    assert deltas["vaqueros"]["sell_through_rate_change"] == -0.15
    assert deltas["vaqueros"]["avg_sale_price_change"] == -2.0


def test_compute_deltas_skips_categories_missing_in_previous() -> None:
    latest = _metrics(
        {}, {"polos": {"sell_through_rate": 0.2, "avg_sale_price": 10.0, "total_count": 1}}
    )
    previous = _metrics({}, {})

    assert compute_deltas(latest, previous) == {}


def test_compute_deltas_skips_none_metrics() -> None:
    latest = _metrics(
        {}, {"vaqueros": {"sell_through_rate": None, "avg_sale_price": None, "total_count": 0}}
    )
    previous = _metrics(
        {}, {"vaqueros": {"sell_through_rate": None, "avg_sale_price": None, "total_count": 0}}
    )

    assert compute_deltas(latest, previous) == {}


def test_build_prompt_notes_first_report_without_previous() -> None:
    latest = _metrics({"total_count": 3}, {})
    prompt = build_prompt(latest, deltas={}, currency="EUR")

    assert "primer informe" in prompt
    assert "EUR" in prompt


def test_build_prompt_includes_deltas_when_present() -> None:
    latest = _metrics({"total_count": 3}, {})
    deltas = {"vaqueros": {"sell_through_rate_change": -0.15}}

    prompt = build_prompt(latest, deltas, currency="EUR")

    assert "sell_through_rate_change" in prompt
    assert "-0.15" in prompt
