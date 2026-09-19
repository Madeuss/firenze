from contextlib import suppress
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from firenze.paths import OutsideTheRepository, repo_root

Environment = Literal["dev", "staging", "prod"]


def _env_files() -> tuple[str, ...]:
    """O `.env` do diretório atual e o da raiz do repositório.

    Um `.env` relativo ao diretório atual parece razoável até alguém rodar a API
    de dentro de `apps/api` — que é exatamente o que `make api` faz. Ali o
    arquivo da raiz não existia para a configuração, e a chave configurada
    simplesmente sumia: o provedor voltava a ser `none` sem dizer por quê.

    No contêiner não há raiz de repositório acima do pacote, e ali a
    configuração vem do ambiente de qualquer forma.
    """
    arquivos = [".env"]
    with suppress(OutsideTheRepository):
        arquivos.append(str(repo_root() / ".env"))
    return tuple(arquivos)


class Settings(BaseSettings):
    """Process configuration. FIRENZE_ prefix so nothing collides."""

    model_config = SettingsConfigDict(env_prefix="FIRENZE_", env_file=_env_files(), extra="ignore")

    environment: Environment = "dev"
    database_url: str = "postgresql+psycopg://firenze:firenze@localhost:5433/firenze"
    redis_url: str = "redis://localhost:6379/0"
    model_provider: str = "none"
    """Which provider backs the model port: aihub, fake, or none.

    `none` by default even though Magalu's AI Hub is the decision (ADR-0008): a
    default that tried to reach an endpoint nobody has credentials for would
    turn a missing key into a confusing failure."""

    model_name: str = ""
    """Which model at that provider, from its catalog."""

    classifier_model_name: str = ""
    """Which model labels player input. Empty means the same as `model_name`.

    A separate knob because the classifier runs on every turn and reads one
    sentence — the cheapest model in the catalogue is usually enough, and the
    turn budget notices (RN-040)."""

    model_base_url: str = ""
    """Endpoint of the OpenAI-compatible API. The AI Hub console shows it beside
    the API key: `https://api.inferencia.llm.mglu.io/v1`."""

    model_api_key: SecretStr = SecretStr("")
    """Secret so it does not land in a log by accident."""

    access_key: SecretStr = SecretStr("")
    """The shared key that buys the right to start a match. (T-11)

    Empty means this deployment checks nothing, which is what local development
    and the test suite want. A process with `environment` set to `prod` refuses
    to start while it is empty, so open is something you choose rather than
    something you forget."""

    rate_limit_per_minute: int = 30
    """Requests per minute per caller, on the routes that cost money. (T-12)

    Zero disables it. Thirty is above anything a person does by hand and far
    below what a loop does in a second."""


settings = Settings()
