from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["dev", "staging", "prod"]


class Settings(BaseSettings):
    """Process configuration. FIRENZE_ prefix so nothing collides."""

    model_config = SettingsConfigDict(env_prefix="FIRENZE_", env_file=".env", extra="ignore")

    environment: Environment = "dev"
    database_url: str = "postgresql+psycopg://firenze:firenze@localhost:5433/firenze"
    redis_url: str = "redis://localhost:6379/0"
    model_provider: str = "none"
    """Which provider backs the model port: anthropic, fake, or none.

    `none` by default, deliberately. The provider is not decided yet, and a
    default that picked one would make the decision quietly."""

    model_name: str = ""
    """Which model at that provider.

    Empty by default for the same reason the provider is `none`: naming one
    would pick a vendor. Required once a real provider is configured."""


settings = Settings()
