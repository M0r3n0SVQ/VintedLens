import json

import boto3
import pytest
from moto import mock_aws

from reporting import handler as handler_module
from reporting.config import ReportingConfig

REGION = "eu-west-1"
BUCKET = "test-bucket"
REPORT_EMAIL = "loopvtg@example.com"


@pytest.fixture
def fake_config() -> ReportingConfig:
    return ReportingConfig(model_id="amazon.nova-micro-v1:0", max_tokens=400)


def _put_metrics(s3, key: str, overall_total: int, sell_through_rate: float) -> None:
    payload = {
        "currency": "EUR",
        "overall": {"total_count": overall_total},
        "by_category": {
            "vaqueros": {
                "sell_through_rate": sell_through_rate,
                "avg_sale_price": 20.0,
                "total_count": overall_total,
            }
        },
    }
    s3.put_object(Bucket=BUCKET, Key=key, Body=json.dumps(payload).encode("utf-8"))


@mock_aws
def test_handler_skips_when_no_metrics_yet(
    monkeypatch: pytest.MonkeyPatch, fake_config: ReportingConfig
) -> None:
    monkeypatch.setattr(handler_module, "load_config", lambda: fake_config)
    monkeypatch.setattr(handler_module, "DATA_BUCKET", BUCKET)
    monkeypatch.setattr(handler_module, "REPORT_EMAIL", REPORT_EMAIL)

    s3 = boto3.client("s3", region_name=REGION)
    s3.create_bucket(Bucket=BUCKET, CreateBucketConfiguration={"LocationConstraint": REGION})

    result = handler_module.handler({}, context=None)

    assert result == {"status": "skipped", "reason": "no_metrics"}


@mock_aws
def test_handler_sends_report_and_compares_with_previous(
    monkeypatch: pytest.MonkeyPatch, fake_config: ReportingConfig
) -> None:
    monkeypatch.setattr(handler_module, "load_config", lambda: fake_config)
    monkeypatch.setattr(handler_module, "DATA_BUCKET", BUCKET)
    monkeypatch.setattr(handler_module, "REPORT_EMAIL", REPORT_EMAIL)

    captured_prompt: dict[str, str] = {}

    def fake_invoke(prompt: str, model_id: str, max_tokens: int) -> str:
        captured_prompt["prompt"] = prompt
        return "Resumen de prueba generado por Bedrock."

    monkeypatch.setattr(handler_module.bedrock_client, "invoke", fake_invoke)

    sent_emails: list[dict] = []

    class FakeSES:
        def send_email(self, **kwargs):
            sent_emails.append(kwargs)
            return {"MessageId": "fake-message-id"}

    monkeypatch.setattr(handler_module, "ses", FakeSES())

    s3 = boto3.client("s3", region_name=REGION)
    s3.create_bucket(Bucket=BUCKET, CreateBucketConfiguration={"LocationConstraint": REGION})
    _put_metrics(s3, "processed/inventory_20260601_metrics.json", overall_total=5, sell_through_rate=0.5)
    _put_metrics(s3, "processed/inventory_20260701_metrics.json", overall_total=8, sell_through_rate=0.65)

    result = handler_module.handler({}, context=None)

    assert result["status"] == "ok"
    assert result["source_key"] == "processed/inventory_20260701_metrics.json"
    assert result["compared_to"] == "processed/inventory_20260601_metrics.json"
    assert "sell_through_rate_change" in captured_prompt["prompt"]
    assert sent_emails[0]["Destination"]["ToAddresses"] == [REPORT_EMAIL]
    assert sent_emails[0]["Message"]["Body"]["Text"]["Data"] == "Resumen de prueba generado por Bedrock."
