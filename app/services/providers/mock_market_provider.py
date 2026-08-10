from decimal import Decimal

from app.core.exceptions import UnsupportedSymbolError
from app.services.providers.market_provider import MarketProvider


class MockMarketProvider(MarketProvider):
    """
    Mock implementation of the MarketProvider.

    This provider is used during development and testing.
    Prices are stored in memory and simulate an exchange.
    """

    MOCK_PRICES = {
        "BTC": Decimal("168000000.00"),
        "ETH": Decimal("5200000.00"),
        "SOL": Decimal("850000.00"),
    }

    def get_price(
        self,
        symbol: str,
    ) -> Decimal:
        """
        Returns the latest mocked market price.
        """

        symbol = symbol.upper()

        if symbol not in self.MOCK_PRICES:
            raise UnsupportedSymbolError(symbol)

        return self.MOCK_PRICES[symbol]

    def get_supported_symbols(
        self,
    ) -> list[str]:
        """
        Returns every supported mocked symbol.
        """

        return list(self.MOCK_PRICES.keys())