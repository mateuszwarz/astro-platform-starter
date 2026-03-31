from pydantic_settings import BaseSettings
from pydantic import field_validator
import os


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 1
    REDIS_URL: str = "redis://redis:6379/0"
    COMPANY_NAME: str = "Moja Firma"
    COMPANY_NIP: str = ""
    COMPANY_ADDRESS: str = ""

    @field_validator("SECRET_KEY")
    @classmethod
    def secret_key_must_be_strong(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY musi mieć minimum 32 znaki")
        weak_keys = {
            "super-secret-key-change-in-production-min-32-chars",
            "changeme",
            "secret",
        }
        if v in weak_keys:
            raise ValueError("SECRET_KEY jest zbyt słaby — zmień na losowy klucz")
        return v

    @field_validator("DATABASE_URL")
    @classmethod
    def database_url_required(cls, v: str) -> str:
        if not v:
            raise ValueError("DATABASE_URL jest wymagany")
        return v

    model_config = {
        "env_file": ".env",
        "extra": "ignore",
    }


settings = Settings()
