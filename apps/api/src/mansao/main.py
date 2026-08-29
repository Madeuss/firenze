from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

from mansao import __version__
from mansao.config import Ambiente, config


class Saude(BaseModel):
    """Resposta do liveness probe."""

    status: Literal["ok"] = "ok"
    versao: str
    ambiente: Ambiente


def criar_app() -> FastAPI:
    app = FastAPI(
        title="Mansão API",
        version=__version__,
        summary="Core de IA e domínio do jogo de mistério.",
        description=(
            "Dono de todo o domínio determinístico e de toda chamada a LLM (ADR-0003). "
            "O front nunca fala com o provedor de modelo nem com o banco."
        ),
    )

    @app.get("/health", tags=["infra"], summary="Liveness")
    def health() -> Saude:
        """Diz se o processo está de pé. Não toca no banco de propósito:
        readiness com dependências chega junto com o schema (fase 1)."""
        return Saude(versao=__version__, ambiente=config.ambiente)

    return app


app = criar_app()
