from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

from firenze import __version__
from firenze.api import router
from firenze.api.access import check_configuration
from firenze.config import Environment, settings


class Health(BaseModel):
    """Liveness probe response."""

    status: Literal["ok"] = "ok"
    version: str
    environment: Environment


def create_app() -> FastAPI:
    # Before anything is served: a prod process with no access key is a mistake
    # that costs money, and it costs it quietly. (T-11, T-12)
    check_configuration()

    app = FastAPI(
        title="Firenze API",
        version=__version__,
        summary="AI core and domain of the mystery game.",
        description=(
            "Owns the whole deterministic domain and every call to a model (ADR-0003). "
            "The front end never talks to the model provider or to the database."
        ),
    )

    app.include_router(router)

    @app.get("/health", tags=["infra"], summary="Liveness")
    def health() -> Health:
        """Whether the process is up. Deliberately does not touch the database:
        readiness with dependencies arrives with the schema (phase 1)."""
        return Health(version=__version__, environment=settings.environment)

    return app


app = create_app()
