from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["dev", "staging", "prod"]


class Settings(BaseSettings):
    """Process configuration. MANSAO_ prefix so nothing collides."""

    model_config = SettingsConfigDict(env_prefix="MANSAO_", env_file=".env", extra="ignore")

    environment: Environment = "dev"
    database_url: str = "postgresql+psycopg://mansao:mansao@localhost:5433/mansao"
    redis_url: str = "redis://localhost:6379/0"
    veneer_model: str = "claude-opus-5"
    """Which model writes the veneer. Env-switchable because it is the one
    knob that moves cost per case."""


settings = Settings()
