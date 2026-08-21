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


def _put_metrics(
    s3, key: str, overall_total: int, sell_through_rate: float, low_rotation: bool = True
) -> None:
    payload = {
        "currency": "EUR",
        "overall": {"total_count": overall_total},
        "by_category": {
            "vaqueros": {
                "sell_through_rate": sell_through_rate,
                "avg_sale_price": 20.0,
                "total_count": overall_total,
                "low_rotation": low_rotation,
            }
        },
    }
    s3.put_object(Bucket=BUCKET, Key=key, Body=json.dumps(payload).encode("utf-8"))


def _put_clean_csv(s3, key: str) -> None:
    csv_body = (
        "item_id,title,category,brand,size,condition,cost_price,listing_price,"
        "sale_price,listed_date,sold_date,status,platform\n"
        "LV-0001,Vaqueros Levi's 501,vaqueros,levis,M,bueno,8.00,20.00,,2026-07-01,,listed,vinted\n"
    )
    s3.put_object(Bucket=BUCKET, Key=key, Body=csv_body.encode("utf-8"))


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
    fake_response = json.dumps(
        {
            "summary": "Resumen de prueba generado por Bedrock.",
            "suggestions": [
                {
                    "item_id": "LV-0001",
                    "title": "Vaqueros Levi's 501",
                    "suggestion": "Baja el precio un 10%.",
                }
            ],
        }
    )

    def fake_invoke(prompt: str, model_id: str, max_tokens: int) -> str:
        captured_prompt["prompt"] = prompt
        return fake_response

    monkeypatch.setattr(handler_module.bedrock_client, "invoke", fake_invoke)

    sent_emails: list[dict] = []

    class FakeSES:
        def send_email(self, **kwargs):
            sent_emails.append(kwargs)
            return {"MessageId": "fake-message-id"}

    monkeypatch.setattr(handler_module, "ses", FakeSES())

    s3 = boto3.client("s3", region_name=REGION)
    s3.create_bucket(Bucket=BUCKET, CreateBucketConfiguration={"LocationConstraint": REGION})
    _put_metrics(
        s3, "processed/inventory_20260601_metrics.json", overall_total=5, sell_through_rate=0.5
    )
    _put_metrics(
        s3, "processed/inventory_20260701_metrics.json", overall_total=8, sell_through_rate=0.65
    )
    _put_clean_csv(s3, "processed/inventory_20260701_clean.csv")

    result = handler_module.handler({}, context=None)

    assert result["status"] == "ok"
    assert result["source_key"] == "processed/inventory_20260701_metrics.json"
    assert result["compared_to"] == "processed/inventory_20260601_metrics.json"
    assert result["summary_key"] == "processed/inventory_20260701_summary.json"
    assert "sell_through_rate_change" in captured_prompt["prompt"]

    assert sent_emails[0]["Destination"]["ToAddresses"] == [REPORT_EMAIL]
    email_body = sent_emails[0]["Message"]["Body"]["Text"]["Data"]
    assert "Resumen de prueba generado por Bedrock." in email_body
    assert "Vaqueros Levi's 501: Baja el precio un 10%." in email_body

    summary_object = s3.get_object(Bucket=BUCKET, Key=result["summary_key"])
    summary_payload = json.loads(summary_object["Body"].read())
    assert summary_payload["summary"] == "Resumen de prueba generado por Bedrock."
    assert summary_payload["suggestions"] == [
        {
            "item_id": "LV-0001",
            "title": "Vaqueros Levi's 501",
            "suggestion": "Baja el precio un 10%.",
        }
    ]
    assert "LV-0001" in captured_prompt["prompt"]
    assert "Vaqueros Levi's 501" in captured_prompt["prompt"]
