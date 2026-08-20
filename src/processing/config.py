"""Configuración de la Lambda de procesamiento, leída de Parameter Store.

Vivir en Parameter Store en vez de variables de entorno de la Lambda
permite cambiar el umbral de rotación baja sin redesplegar código.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

import boto3
from botocore.exceptions import ClientError

PARAMETER_PREFIX = "/{project}/{environment}/processing".format(
    project=os.environ.get("PROJECT", "vintedlens"),
    environment=os.environ.get("ENVIRONMENT", "dev"),
)


@dataclass(frozen=True)
class ProcessingConfig:
    raw_prefix: str
    processed_prefix: str
    low_sell_through_threshold: float
    currency: str


@lru_cache(maxsize=1)
def load_config() -> ProcessingConfig:
    """Lee la configuración de procesamiento desde Parameter Store.

    Cacheada en memoria del proceso: en una Lambda "warm" evita releer
    Parameter Store en cada invocación.

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
        return ProcessingConfig(
            raw_prefix=values["raw_prefix"],
            processed_prefix=values["processed_prefix"],
            low_sell_through_threshold=float(values["low_sell_through_threshold"]),
            currency=values["currency"],
        )
    except KeyError as exc:
        raise RuntimeError(f"falta el parámetro {exc} en {PARAMETER_PREFIX}") from exc
    except ValueError as exc:
        raise RuntimeError("low_sell_through_threshold no es un número válido") from exc
