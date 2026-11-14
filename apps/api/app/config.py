from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "postgresql+psycopg://secureagent:secureagent@localhost:5432/secureagent"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "dev-only-change-me"
    jwt_algorithm: str = "HS256"
    token_minutes: int = 60
    cors_origins: str = "http://localhost:3000"

@lru_cache
def get_settings() -> Settings:
    return Settings()
