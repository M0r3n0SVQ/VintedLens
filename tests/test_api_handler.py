import json

import boto3
import pytest
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
    assert body == {"latest": None, "history": []}


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

    result = handler_module.handler(_event(API_KEY), context=None)

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["latest"]["overall"]["total_count"] == 8
    assert len(body["history"]) == 1
    assert body["history"][0]["overall"]["total_count"] == 5
