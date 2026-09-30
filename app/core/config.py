from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    APP_NAME: str = "QI API"
    APP_VERSION: str = "5.0.0"

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/db_qi_agent")

    # JWT
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: List[str] = ["https://qi.mibt.my.id"]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.JWT_SECRET_KEY:
            import warnings
            warnings.warn(
                "JWT_SECRET_KEY is not set! Using insecure default. "
                "Set JWT_SECRET_KEY environment variable in production.",
                RuntimeWarning,
            )
            self.JWT_SECRET_KEY = "change-me-in-production"


settings = Settings()
