from decimal import Decimal

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
        extra="ignore",
        case_sensitive=True,
    )

    APP_NAME: str = "TradeFlow AI"

    APP_VERSION: str = "1.0.0"

    DEBUG: bool = True

    ENVIRONMENT: str = "development"

    # Market data provider.
    #
    # mock:
    #     Uses the local/mock market provider.
    #
    # quidax:
    #     Uses live Quidax market data.
    MARKET_PROVIDER: str = "mock"

    # Trade execution mode.
    #
    # paper:
    #     No real exchange order.
    #
    # live:
    #     Uses QuidaxExecutionProvider.
    TRADING_MODE: str = "paper"

    # Automation safety switch.
    #
    # This is deliberately separate from TRADING_MODE.
    #
    # Even when TRADING_MODE=live, automated trading remains
    # disabled unless this is explicitly true.
    AUTOMATION_LIVE_TRADING: bool = False

    QUIDAX_BASE_URL: str = (
        "https://openapi.quidax.io/exchange-open-api/api/v1"
    )

    QUIDAX_API_KEY: str = ""

    QUIDAX_SECRET_KEY: str = ""

    REQUEST_TIMEOUT: int = 10

    QUIDAX_ORDER_POLL_INTERVAL: float = 0.5

    QUIDAX_ORDER_TIMEOUT: int = 15

    AUTOMATION_POLL_INTERVAL: float = 5.0

    # Quidax market orders are taker orders.
    QUIDAX_TRADING_FEE_RATE: Decimal = Decimal(
        "0.001"
    )


settings = Settings()