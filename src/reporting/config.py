"""Configuración de la Lambda de reporting, leída de Parameter Store.

El modelo de Bedrock y el límite de tokens viven aquí para poder
cambiarlos (por ejemplo, a un modelo más barato o más capaz) sin
redesplegar código.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

import boto3
from botocore.exceptions import ClientError

PARAMETER_PREFIX = "/{project}/{environment}/reporting".format(
    project=os.environ.get("PROJECT", "vintedlens"),
    environment=os.environ.get("ENVIRONMENT", "dev"),
)


@dataclass(frozen=True)
class ReportingConfig:
    model_id: str
    max_tokens: int


@lru_cache(maxsize=1)
def load_config() -> ReportingConfig:
    """Lee la configuración de reporting desde Parameter Store.

    Raises:
        RuntimeError: si falta un parámetro o su valor es inválido.
    """
    region = os.environ.get("AWS_REGION", "eu-west-1")
    client = boto3.client("ssm", region_name=region)

    try:
        response = client.get_parameters_by_path(Path=PARAMETER_PREFIX, Recursive=False)
    except ClientError as exc:
        raise RuntimeError(
            f"no se pudo leer la configuración de Parameter Store en {PARAMETER_PREFIX}: {exc}"
        ) from exc

    values = {p["Name"].rsplit("/", 1)[-1]: p["Value"] for p in response["Parameters"]}

    try:
        return ReportingConfig(
            model_id=values["model_id"],
            max_tokens=int(values["max_tokens"]),
        )
    except KeyError as exc:
        raise RuntimeError(f"falta el parámetro {exc} en {PARAMETER_PREFIX}") from exc
    except ValueError as exc:
        raise RuntimeError("max_tokens no es un entero válido") from exc
