
from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    app_env: str = "development"

    database_url: str = (
        "postgresql+psycopg://secureagent:"
        "secureagent@localhost:5432/secureagent"
    )

    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "dev-only-change-me"
    jwt_algorithm: str = "HS256"

    token_minutes: int = Field(
        default=60,
        ge=1,
        le=1440,
    )

    cors_origins: str = "http://localhost:3000"

    @model_validator(mode="after")
    def validate_security_configuration(self):
        environment = self.app_env.strip().lower()

        if environment not in {
            "development",
            "test",
            "testing",
            "production",
        }:
            raise ValueError(
                "APP_ENV must be development, "
                "test, testing, or production"
            )

        self.app_env = environment

        if self.jwt_algorithm != "HS256":
            raise ValueError(
                "JWT_ALGORITHM must be HS256"
            )

        if environment == "production":
            secret = self.jwt_secret.strip()

            if (
                len(secret) < 32
                or secret == "dev-only-change-me"
                or len(set(secret)) < 12
            ):
                raise ValueError(
                    "Production JWT_SECRET must be "
                    "at least 32 characters and "
                    "use a strong random value"
                )

            default_database_url = (
                "postgresql+psycopg://secureagent:"
                "secureagent@localhost:5432/secureagent"
            )

            if self.database_url == default_database_url:
                raise ValueError(
                    "Production DATABASE_URL cannot "
                    "use development defaults"
                )

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
