from app.core.settings import settings
from app.services.providers.market_provider import MarketProvider
from app.services.providers.mock_market_provider import (
    MockMarketProvider,
)
from app.services.providers.quidax_market_provider import (
    QuidaxMarketProvider,
)


class ProviderFactory:
    """
    Creates the configured market data provider.

    The provider is selected from application settings.

    Examples:

        MARKET_PROVIDER=mock

        MARKET_PROVIDER=quidax
    """

    @staticmethod
    def create() -> MarketProvider:
        """
        Returns the configured market provider.
        """

        provider = settings.MARKET_PROVIDER.lower()

        if provider == "mock":
            return MockMarketProvider()

        if provider == "quidax":
            return QuidaxMarketProvider()

        raise ValueError(
            f"Unsupported market provider: {provider}"
        )