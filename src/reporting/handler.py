"""Lambda de reporting: resume las métricas más recientes con Bedrock y
las envía por email vía SES.

Disparada periódicamente por una regla EventBridge programada (no por
cada subida de CSV: el objetivo es un resumen periódico, no un email
por cada archivo).
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

import boto3
from botocore.exceptions import ClientError

from . import bedrock_client
from .config import load_config
from .summarizer import build_prompt, compute_deltas, parse_summary_response

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Región explícita: en Lambda AWS_REGION siempre está definida, pero un
# boto3.client() sin region_name falla en cuanto no hay ninguna región
# configurada en el entorno (por ejemplo, un runner de CI limpio).
_region = os.environ.get("AWS_REGION", "eu-west-1")
s3 = boto3.client("s3", region_name=_region)
ses = boto3.client("ses", region_name=_region)

DATA_BUCKET = os.environ.get("DATA_BUCKET", "")
REPORT_EMAIL = os.environ.get("REPORT_EMAIL", "")


def _list_metrics_objects() -> list[dict[str, Any]]:
    """Lista los *_metrics.json de processed/, más recientes primero."""
    paginator = s3.get_paginator("list_objects_v2")
    objects: list[dict[str, Any]] = []
    for page in paginator.paginate(Bucket=DATA_BUCKET, Prefix="processed/"):
        for obj in page.get("Contents", []):
            if obj["Key"].endswith("_metrics.json"):
                objects.append(obj)
    # Desempate por Key cuando dos objetos comparten LastModified (puede
    # pasar si dos subidas caen en el mismo segundo): nuestros nombres de
    # archivo incluyen fecha, así que el desempate lexicográfico coincide
    # con el orden cronológico real.
    return sorted(objects, key=lambda o: (o["LastModified"], o["Key"]), reverse=True)


def _load_json(key: str) -> dict:
    body = s3.get_object(Bucket=DATA_BUCKET, Key=key)["Body"].read()
    return json.loads(body)


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Punto de entrada de la Lambda: genera y envía el informe periódico."""
    config = load_config()

    metrics_objects = _list_metrics_objects()
    if not metrics_objects:
        logger.info("No hay métricas en processed/ todavía, no se genera informe.")
        return {"status": "skipped", "reason": "no_metrics"}

    latest = _load_json(metrics_objects[0]["Key"])
    previous = _load_json(metrics_objects[1]["Key"]) if len(metrics_objects) > 1 else None

    deltas = compute_deltas(latest, previous)
    prompt = build_prompt(latest, deltas, latest.get("currency", "EUR"))

    raw_response = bedrock_client.invoke(
        prompt=prompt,
        model_id=config.model_id,
        max_tokens=config.max_tokens,
    )
    parsed = parse_summary_response(raw_response)
    summary_text = parsed["summary"]
    suggestions = parsed["suggestions"]

    email_body = summary_text
    if suggestions:
        bullet_lines = "\n".join(f"- {s['category']}: {s['suggestion']}" for s in suggestions)
        email_body = f"{summary_text}\n\nSugerencias:\n{bullet_lines}"

    try:
        ses.send_email(
            Source=REPORT_EMAIL,
            Destination={"ToAddresses": [REPORT_EMAIL]},
            Message={
                "Subject": {"Data": "VintedLens - resumen de inventario", "Charset": "UTF-8"},
                "Body": {"Text": {"Data": email_body, "Charset": "UTF-8"}},
            },
        )
    except ClientError:
        logger.exception("No se pudo enviar el email de reporting")
        raise

    source_key = metrics_objects[0]["Key"]
    summary_key = source_key.replace("_metrics.json", "_summary.json")
    summary_payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source_key": source_key,
        "compared_to": metrics_objects[1]["Key"] if previous else None,
        "summary": summary_text,
        "suggestions": suggestions,
    }

    try:
        s3.put_object(
            Bucket=DATA_BUCKET,
            Key=summary_key,
            Body=json.dumps(summary_payload, ensure_ascii=False, indent=2).encode("utf-8"),
            ContentType="application/json",
        )
    except ClientError:
        logger.exception("No se pudo escribir %s", summary_key)
        raise

    logger.info(
        "Informe enviado a %s a partir de %s (comparado con %s)",
        REPORT_EMAIL,
        source_key,
        metrics_objects[1]["Key"] if previous else "ninguno",
    )

    return {
        "status": "ok",
        "source_key": source_key,
        "summary_key": summary_key,
        "compared_to": metrics_objects[1]["Key"] if previous else None,
    }
