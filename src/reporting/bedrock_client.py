"""Wrapper fino sobre la Converse API de Bedrock.

Aislado en su propio módulo para poder monkeypatchear invoke() en los
tests sin depender de que moto sepa mockear Bedrock.
"""

from __future__ import annotations

import os

import boto3


def invoke(prompt: str, model_id: str, max_tokens: int) -> str:
    """Pide a Bedrock un texto a partir del prompt y devuelve la respuesta.

    Raises:
        RuntimeError: si Bedrock no devuelve el texto esperado (p. ej.
            respuesta vacía o con un formato inesperado).
    """
    region = os.environ.get("AWS_REGION", "eu-west-1")
    client = boto3.client("bedrock-runtime", region_name=region)

    response = client.converse(
        modelId=model_id,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": max_tokens, "temperature": 0.4},
    )

    try:
        return response["output"]["message"]["content"][0]["text"]
    except (KeyError, IndexError) as exc:
        raise RuntimeError(f"respuesta de Bedrock con formato inesperado: {response}") from exc
