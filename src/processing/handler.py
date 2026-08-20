"""Lambda de procesamiento: limpia el CSV subido a raw/ y calcula métricas.

Disparada por una regla EventBridge sobre eventos "Object Created" de
S3 filtrados por el prefijo raw/. Escribe en processed/ el CSV
validado y un JSON con las métricas por categoría.
"""

from __future__ import annotations

import csv
import io
import json
import logging
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Any

import boto3
from botocore.exceptions import ClientError

from .config import load_config
from .metrics import compute_all_metrics
from .parsing import InventoryItem, parse_csv

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")

CSV_FIELDNAMES = (
    "item_id",
    "title",
    "category",
    "brand",
    "size",
    "condition",
    "cost_price",
    "listing_price",
    "sale_price",
    "listed_date",
    "sold_date",
    "status",
    "platform",
)


def _item_to_row(item: InventoryItem) -> dict[str, str]:
    return {
        "item_id": item.item_id,
        "title": item.title,
        "category": item.category,
        "brand": item.brand,
        "size": item.size,
        "condition": item.condition,
        "cost_price": f"{item.cost_price:.2f}",
        "listing_price": f"{item.listing_price:.2f}",
        "sale_price": f"{item.sale_price:.2f}" if item.sale_price is not None else "",
        "listed_date": item.listed_date.isoformat(),
        "sold_date": item.sold_date.isoformat() if item.sold_date else "",
        "status": item.status,
        "platform": item.platform,
    }


def _write_clean_csv(items: list[InventoryItem]) -> bytes:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(CSV_FIELDNAMES))
    writer.writeheader()
    for item in items:
        writer.writerow(_item_to_row(item))
    return buffer.getvalue().encode("utf-8")


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Punto de entrada de la Lambda: procesa un evento S3 Object Created."""
    detail = event["detail"]
    bucket = detail["bucket"]["name"]
    source_key = detail["object"]["key"]

    config = load_config()

    if not source_key.startswith(config.raw_prefix):
        logger.info("Ignorando objeto fuera de %s: %s", config.raw_prefix, source_key)
        return {"status": "skipped", "key": source_key}

    logger.info("Procesando s3://%s/%s", bucket, source_key)

    try:
        response = s3.get_object(Bucket=bucket, Key=source_key)
        csv_text = response["Body"].read().decode("utf-8")
    except ClientError:
        logger.exception("No se pudo leer s3://%s/%s", bucket, source_key)
        raise

    items, errors = parse_csv(csv_text)
    metrics = compute_all_metrics(items, config.low_sell_through_threshold)

    basename = PurePosixPath(source_key).stem
    clean_key = f"{config.processed_prefix}{basename}_clean.csv"
    metrics_key = f"{config.processed_prefix}{basename}_metrics.json"

    metrics_payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_key": source_key,
        "currency": config.currency,
        "low_sell_through_threshold": config.low_sell_through_threshold,
        "valid_row_count": len(items),
        "invalid_row_count": len(errors),
        "row_errors": [
            {"row": e.row_number, "item_id": e.item_id, "reason": e.reason} for e in errors
        ],
        **metrics,
    }

    try:
        s3.put_object(
            Bucket=bucket,
            Key=clean_key,
            Body=_write_clean_csv(items),
            ContentType="text/csv",
        )
        s3.put_object(
            Bucket=bucket,
            Key=metrics_key,
            Body=json.dumps(metrics_payload, ensure_ascii=False, indent=2).encode("utf-8"),
            ContentType="application/json",
        )
    except ClientError:
        logger.exception("No se pudo escribir la salida en %s", config.processed_prefix)
        raise

    logger.info(
        "OK: %d items válidos, %d con error. Salida: %s, %s",
        len(items),
        len(errors),
        clean_key,
        metrics_key,
    )

    return {
        "status": "ok",
        "clean_key": clean_key,
        "metrics_key": metrics_key,
        "valid_row_count": len(items),
        "invalid_row_count": len(errors),
    }
