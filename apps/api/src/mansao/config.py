from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

Ambiente = Literal["dev", "staging", "prod"]


class Configuracao(BaseSettings):
    """Configuração do processo. Prefixo MANSAO_ para não colidir com nada."""

    model_config = SettingsConfigDict(env_prefix="MANSAO_", env_file=".env", extra="ignore")

    ambiente: Ambiente = "dev"
    database_url: str = "postgresql+psycopg://mansao:mansao@localhost:5433/mansao"
    redis_url: str = "redis://localhost:6379/0"


config = Configuracao()
