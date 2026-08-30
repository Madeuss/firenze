from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["dev", "staging", "prod"]


class Settings(BaseSettings):
    """Process configuration. FIRENZE_ prefix so nothing collides."""

    model_config = SettingsConfigDict(env_prefix="FIRENZE_", env_file=".env", extra="ignore")

    environment: Environment = "dev"
    database_url: str = "postgresql+psycopg://firenze:firenze@localhost:5433/firenze"
    redis_url: str = "redis://localhost:6379/0"
    veneer_model: str = "claude-haiku-4-5"
    """Which model writes the veneer. Env-switchable because it is the one
    knob that moves cost per case."""


settings = Settings()
