"""Lambda de API: expone las métricas más recientes al dashboard.

Detrás de API Gateway (HTTP API). Protegida por una clave compartida
en el header x-api-key en vez de un mecanismo nativo de API Gateway
(API keys de REST API), para poder seguir usando HTTP API, más barato
y simple. El dashboard llama a esto desde el servidor (Next.js),
nunca desde el navegador, así la clave no se expone al cliente.
"""

from __future__ import annotations

import hmac
import json
import logging
import os
from typing import Any

import boto3
from botocore.exceptions import ClientError

from .config import load_config

logger = logging.getLogger()
logger.setLevel(logging.INFO)

_region = os.environ.get("AWS_REGION", "eu-west-1")
s3 = boto3.client("s3", region_name=_region)

DATA_BUCKET = os.environ.get("DATA_BUCKET", "")
HISTORY_LIMIT = 10


def _response(status: int, body: dict) -> dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, ensure_ascii=False),
    }


def _list_processed_objects(suffix: str) -> list[dict[str, Any]]:
    """Lista los objetos de processed/ con el sufijo dado, más recientes primero."""
    paginator = s3.get_paginator("list_objects_v2")
    objects: list[dict[str, Any]] = []
    for page in paginator.paginate(Bucket=DATA_BUCKET, Prefix="processed/"):
        for obj in page.get("Contents", []):
            if obj["Key"].endswith(suffix):
                objects.append(obj)
    return sorted(objects, key=lambda o: (o["LastModified"], o["Key"]), reverse=True)


def _load_json(key: str) -> dict:
    body = s3.get_object(Bucket=DATA_BUCKET, Key=key)["Body"].read()
    return json.loads(body)


def _is_authorized(event: dict[str, Any], expected_key: str) -> bool:
    headers = event.get("headers") or {}
    provided_key = headers.get("x-api-key", "")
    return hmac.compare_digest(provided_key, expected_key)


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Punto de entrada: devuelve el snapshot más reciente y un historial corto."""
    config = load_config()

    if not _is_authorized(event, config.api_key):
        return _response(401, {"error": "unauthorized"})

    metrics_objects = _list_processed_objects("_metrics.json")
    if not metrics_objects:
        return _response(200, {"latest": None, "history": [], "ai_summary": None})

    try:
        latest = _load_json(metrics_objects[0]["Key"])
        history = [_load_json(obj["Key"]) for obj in metrics_objects[1 : HISTORY_LIMIT + 1]]

        # El resumen de IA lo genera una Lambda distinta (reporting), en su
        # propio horario: puede no existir todavía, o no corresponder
        # exactamente al último *_metrics.json si el reporting no se ha
        # ejecutado desde la última subida. Se expone el más reciente que
        # haya, sea cual sea su fecha.
        summary_objects = _list_processed_objects("_summary.json")
        ai_summary = _load_json(summary_objects[0]["Key"]) if summary_objects else None
    except ClientError:
        logger.exception("No se pudieron leer los datos de %s", DATA_BUCKET)
        return _response(500, {"error": "internal_error"})

    return _response(200, {"latest": latest, "history": history, "ai_summary": ai_summary})
