from decimal import Decimal

from app.core.exceptions import UnsupportedSymbolError


class PriceService:
    """Provides market prices for supported assets."""

    MOCK_PRICES = {
        "BTC": Decimal("168000000.00"),
        "ETH": Decimal("5200000.00"),
        "SOL": Decimal("850000.00"),
    }

    @classmethod
    def get_price(cls, symbol: str) -> Decimal:
        """
        Returns the current market price for a symbol.

        For the MVP, prices are mocked.
        """
        symbol = symbol.upper()

        if symbol not in cls.MOCK_PRICES:
            raise UnsupportedSymbolError(symbol)

        return cls.MOCK_PRICES[symbol]