import json

import boto3
import pytest
from botocore.exceptions import ClientError
from moto import mock_aws

from api import handler as handler_module
from api.config import ApiConfig

REGION = "eu-west-1"
BUCKET = "test-bucket"
API_KEY = "test-key-123"


@pytest.fixture
def fake_config() -> ApiConfig:
    return ApiConfig(api_key=API_KEY)


def _event(api_key: str | None) -> dict:
    headers = {"x-api-key": api_key} if api_key is not None else {}
    return {"headers": headers}


def _put_metrics(s3, key: str, total_count: int) -> None:
    s3.put_object(
        Bucket=BUCKET,
        Key=key,
        Body=json.dumps({"overall": {"total_count": total_count}, "by_category": {}}).encode(),
    )


@mock_aws
def test_handler_rejects_missing_or_wrong_key(
    monkeypatch: pytest.MonkeyPatch, fake_config: ApiConfig
) -> None:
    monkeypatch.setattr(handler_module, "load_config", lambda: fake_config)
    monkeypatch.setattr(handler_module, "DATA_BUCKET", BUCKET)

    assert handler_module.handler(_event(None), context=None)["statusCode"] == 401
    assert handler_module.handler(_event("wrong-key"), context=None)["statusCode"] == 401


@mock_aws
def test_handler_returns_empty_when_no_metrics_yet(
    monkeypatch: pytest.MonkeyPatch, fake_config: ApiConfig
) -> None:
    monkeypatch.setattr(handler_module, "load_config", lambda: fake_config)
    monkeypatch.setattr(handler_module, "DATA_BUCKET", BUCKET)

    s3 = boto3.client("s3", region_name=REGION)
    s3.create_bucket(Bucket=BUCKET, CreateBucketConfiguration={"LocationConstraint": REGION})

    result = handler_module.handler(_event(API_KEY), context=None)

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body == {"latest": None, "history": [], "ai_summary": None}


@mock_aws
def test_handler_returns_latest_and_history(
    monkeypatch: pytest.MonkeyPatch, fake_config: ApiConfig
) -> None:
    monkeypatch.setattr(handler_module, "load_config", lambda: fake_config)
    monkeypatch.setattr(handler_module, "DATA_BUCKET", BUCKET)

    s3 = boto3.client("s3", region_name=REGION)
    s3.create_bucket(Bucket=BUCKET, CreateBucketConfiguration={"LocationConstraint": REGION})
    _put_metrics(s3, "processed/inventory_20260601_metrics.json", total_count=5)
    _put_metrics(s3, "processed/inventory_20260701_metrics.json", total_count=8)
    s3.put_object(
        Bucket=BUCKET,
        Key="processed/inventory_20260701_summary.json",
        Body=json.dumps({"summary": "Todo bien.", "suggestions": []}).encode(),
    )

    result = handler_module.handler(_event(API_KEY), context=None)

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["latest"]["overall"]["total_count"] == 8
    assert len(body["history"]) == 1
    assert body["history"][0]["overall"]["total_count"] == 5
    assert body["ai_summary"] == {"summary": "Todo bien.", "suggestions": []}


@mock_aws
def test_handler_returns_ai_summary_none_when_reporting_has_not_run(
    monkeypatch: pytest.MonkeyPatch, fake_config: ApiConfig
) -> None:
    monkeypatch.setattr(handler_module, "load_config", lambda: fake_config)
    monkeypatch.setattr(handler_module, "DATA_BUCKET", BUCKET)

    s3 = boto3.client("s3", region_name=REGION)
    s3.create_bucket(Bucket=BUCKET, CreateBucketConfiguration={"LocationConstraint": REGION})
    _put_metrics(s3, "processed/inventory_20260701_metrics.json", total_count=8)

    result = handler_module.handler(_event(API_KEY), context=None)

    body = json.loads(result["body"])
    assert body["ai_summary"] is None


def test_handler_returns_500_when_s3_listing_fails(
    monkeypatch: pytest.MonkeyPatch, fake_config: ApiConfig
) -> None:
    """El listado inicial de processed/ también debe fallar de forma
    controlada, no solo las lecturas posteriores (bug real: solo estaba
    envuelto en try/except el bloque a partir de _load_json)."""
    monkeypatch.setattr(handler_module, "load_config", lambda: fake_config)

    def _boom(suffix: str) -> list[dict]:
        raise ClientError({"Error": {"Code": "500", "Message": "boom"}}, "ListObjectsV2")

    monkeypatch.setattr(handler_module, "_list_processed_objects", _boom)

    result = handler_module.handler(_event(API_KEY), context=None)

    assert result["statusCode"] == 500
    assert json.loads(result["body"]) == {"error": "internal_error"}
