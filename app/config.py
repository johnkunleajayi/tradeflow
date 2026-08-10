from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings.

    Values are automatically loaded from environment
    variables or a .env file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
        case_sensitive=True,
    )

    APP_NAME: str = "TradeFlow AI"

    APP_VERSION: str = "1.0.0"

    DEBUG: bool = True

    ENVIRONMENT: str = "development"

    MARKET_PROVIDER: str = "mock"

    TRADING_MODE: str = "paper"

    QUIDAX_BASE_URL: str = (
        "https://www.quidax.com/api/v1"
    )

    QUIDAX_API_KEY: str = ""

    QUIDAX_SECRET_KEY: str = ""

    REQUEST_TIMEOUT: int = 10


settings = Settings()