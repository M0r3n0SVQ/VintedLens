import os
import pathlib

import pytest

# Credenciales falsas para moto. Los handlers crean sus clientes boto3
# a nivel de módulo, en el import, antes de que ningún @mock_aws entre
# en juego, así que botocore necesita encontrar algo con pinta de
# credencial ya en el entorno al arrancar, o falla con
# NoCredentialsError incluso dentro de un test mockeado. En un runner
# de CI limpio no hay nada de esto por defecto (a diferencia de una
# máquina de desarrollo con ~/.aws/credentials configurado).
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("AWS_SECURITY_TOKEN", "testing")
os.environ.setdefault("AWS_SESSION_TOKEN", "testing")
os.environ.setdefault("AWS_DEFAULT_REGION", "eu-west-1")

SAMPLE_CSV_PATH = (
    pathlib.Path(__file__).resolve().parent.parent / "data" / "samples" / "inventory_sample.csv"
)


@pytest.fixture
def sample_csv_text() -> str:
    return SAMPLE_CSV_PATH.read_text(encoding="utf-8")
