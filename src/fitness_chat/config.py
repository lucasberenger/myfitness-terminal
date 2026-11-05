from functools import lru_cache
from pydantic import SecretStr, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    database_url: str
    timezone: str = 'America/Sao_Paulo'
    groq_api_key: SecretStr = SecretStr('')
    groq_model: str = 'llama-3.3-70b-versatile'
    agent_max_rounds: int = Field(default=6, ge=1, le=20)
    agent_timeout_seconds: float = Field(default=30, gt=0, le=120)


@lru_cache
def get_settings() -> Settings:
    return Settings()
