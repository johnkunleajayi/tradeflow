from decimal import Decimal

from app.schemas.market import MarketPriceResponse
from app.services.providers.provider_factory import (
    ProviderFactory,
)


class MarketDataService:
    """
    Provides market data.

    Responsibilities:
    - Current prices
    - Supported assets
    - Market summaries

    This service is completely provider-agnostic.

    It never knows whether prices come from:

    - MockMarketProvider
    - QuidaxMarketProvider
    - BinanceMarketProvider
    - CoinbaseMarketProvider
    """

    def __init__(self):
        self.provider = ProviderFactory.create()

    def get_all_prices(
        self,
    ) -> list[MarketPriceResponse]:
        """
        Returns prices for every supported asset.
        """

        prices: list[MarketPriceResponse] = []

        for symbol in self.provider.get_supported_symbols():

            prices.append(
                MarketPriceResponse(
                    symbol=symbol,
                    price=self.provider.get_price(symbol),
                )
            )

        return prices

    def get_price(
        self,
        symbol: str,
    ) -> MarketPriceResponse:
        """
        Returns the latest market price for a symbol.
        """

        symbol = symbol.upper()

        price: Decimal = self.provider.get_price(symbol)

        return MarketPriceResponse(
            symbol=symbol,
            price=price,
        )