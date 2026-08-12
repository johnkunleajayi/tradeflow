from decimal import Decimal

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings.

    Values are automatically loaded from environment variables
    or a .env file.
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
    TRADING_MODE: str = "paper"

    QUIDAX_BASE_URL: str = (
        "https://openapi.quidax.io/exchange-open-api/api/v1"
    )

    QUIDAX_API_KEY: str = ""
    QUIDAX_SECRET_KEY: str = ""

    REQUEST_TIMEOUT: int = 10

    QUIDAX_ORDER_POLL_INTERVAL: float = 0.5
    QUIDAX_ORDER_TIMEOUT: int = 15

    # Quidax current spot market maker/taker trading fee.
    # Market orders are taker orders.
    QUIDAX_TRADING_FEE_RATE: Decimal = Decimal("0.001")


settings = Settings()