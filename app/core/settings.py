from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings.

    Values are automatically loaded from
    environment variables or a .env file.
    """

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "TradeFlow AI"

    APP_VERSION: str = "1.0.0"

    ENVIRONMENT: str = "development"

    MARKET_PROVIDER: str = "mock"

    QUIDAX_BASE_URL: str = "https://www.quidax.com/api/v1"

    QUIDAX_API_KEY: str = ""

    QUIDAX_SECRET_KEY: str = ""

    REQUEST_TIMEOUT: int = 10


settings = Settings()