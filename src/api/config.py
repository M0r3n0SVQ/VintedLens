"""Configuración de la Lambda de API: la clave que protege el endpoint.

Vive en Parameter Store como SecureString (no en variables de entorno
de la Lambda) para que ni siquiera alguien con acceso de lectura a la
consola de Lambda la vea en texto plano sin permiso explícito de KMS.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

import boto3
from botocore.exceptions import ClientError

PARAMETER_NAME = "/{project}/{environment}/api/api_key".format(
    project=os.environ.get("PROJECT", "vintedlens"),
    environment=os.environ.get("ENVIRONMENT", "dev"),
)


@dataclass(frozen=True)
class ApiConfig:
    api_key: str


@lru_cache(maxsize=1)
def load_config() -> ApiConfig:
    """Lee la API key desde Parameter Store (SecureString).

    Raises:
        RuntimeError: si el parámetro no existe o no se puede leer.
    """
    region = os.environ.get("AWS_REGION", "eu-west-1")
    client = boto3.client("ssm", region_name=region)

    try:
        response = client.get_parameter(Name=PARAMETER_NAME, WithDecryption=True)
    except ClientError as exc:
        raise RuntimeError(
            f"no se pudo leer la configuración de Parameter Store en {PARAMETER_NAME}: {exc}"
        ) from exc

    return ApiConfig(api_key=response["Parameter"]["Value"])
