from fastapi.testclient import TestClient

from mansao import __version__
from mansao.main import app

cliente = TestClient(app)


def test_health_responde_ok() -> None:
    resposta = cliente.get("/health")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok", "version": __version__, "environment": "dev"}


def test_openapi_e_servido() -> None:
    esquema = cliente.get("/openapi.json").json()

    assert esquema["info"]["title"] == "Mansão API"
    assert "/health" in esquema["paths"]
