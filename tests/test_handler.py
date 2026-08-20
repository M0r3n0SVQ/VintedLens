import json

import boto3
import pytest
from moto import mock_aws

from processing import handler as handler_module
from processing.config import ProcessingConfig

REGION = "eu-west-1"


@pytest.fixture
def fake_config() -> ProcessingConfig:
    return ProcessingConfig(
        raw_prefix="raw/",
        processed_prefix="processed/",
        low_sell_through_threshold=0.3,
        currency="EUR",
    )


@mock_aws
def test_handler_writes_clean_csv_and_metrics(
    monkeypatch: pytest.MonkeyPatch, sample_csv_text: str, fake_config: ProcessingConfig
) -> None:
    monkeypatch.setattr(handler_module, "load_config", lambda: fake_config)

    bucket = "test-bucket"
    key = "raw/inventory_sample.csv"

    s3 = boto3.client("s3", region_name=REGION)
    s3.create_bucket(Bucket=bucket, CreateBucketConfiguration={"LocationConstraint": REGION})
    s3.put_object(Bucket=bucket, Key=key, Body=sample_csv_text.encode("utf-8"))

    event = {"detail": {"bucket": {"name": bucket}, "object": {"key": key}}}

    result = handler_module.handler(event, context=None)

    assert result["status"] == "ok"
    assert result["invalid_row_count"] == 0
    assert result["valid_row_count"] == 8

    clean_body = s3.get_object(Bucket=bucket, Key=result["clean_key"])["Body"].read()
    assert b"item_id" in clean_body
    assert clean_body.count(b"\n") == 9  # cabecera + 8 filas

    metrics_body = s3.get_object(Bucket=bucket, Key=result["metrics_key"])["Body"].read()
    metrics = json.loads(metrics_body)

    assert metrics["source_key"] == key
    assert metrics["invalid_row_count"] == 0
    assert metrics["overall"]["total_count"] == 8
    assert "polos" in metrics["by_category"]


@mock_aws
def test_handler_skips_objects_outside_raw_prefix(
    monkeypatch: pytest.MonkeyPatch, fake_config: ProcessingConfig
) -> None:
    monkeypatch.setattr(handler_module, "load_config", lambda: fake_config)

    event = {
        "detail": {
            "bucket": {"name": "test-bucket"},
            "object": {"key": "processed/inventory_sample_clean.csv"},
        }
    }

    result = handler_module.handler(event, context=None)

    assert result == {"status": "skipped", "key": "processed/inventory_sample_clean.csv"}
