import pathlib

import pytest

SAMPLE_CSV_PATH = (
    pathlib.Path(__file__).resolve().parent.parent / "data" / "samples" / "inventory_sample.csv"
)


@pytest.fixture
def sample_csv_text() -> str:
    return SAMPLE_CSV_PATH.read_text(encoding="utf-8")
