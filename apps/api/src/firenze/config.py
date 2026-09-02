from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["dev", "staging", "prod"]


class Settings(BaseSettings):
    """Process configuration. FIRENZE_ prefix so nothing collides."""

    model_config = SettingsConfigDict(env_prefix="FIRENZE_", env_file=".env", extra="ignore")

    environment: Environment = "dev"
    database_url: str = "postgresql+psycopg://firenze:firenze@localhost:5433/firenze"
    redis_url: str = "redis://localhost:6379/0"
    model_provider: str = "none"
    """Which provider backs the model port: prosa, fake, or none.

    `none` by default even though Prosa is the decision (ADR-0008): the product
    is still in pilot, and a default that tried to reach an endpoint nobody has
    credentials for would turn a missing key into a confusing failure."""

    model_name: str = ""
    """Which model at that provider, from its catalog."""

    model_base_url: str = ""
    """Endpoint of the OpenAI-compatible API. Prosa shows it beside the API key."""

    model_api_key: SecretStr = SecretStr("")
    """Secret so it does not land in a log by accident."""


settings = Settings()
