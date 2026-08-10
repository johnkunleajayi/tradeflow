from abc import ABC, abstractmethod
from decimal import Decimal


class MarketProvider(ABC):
    """
    Contract for every market data provider.

    Examples:
    - Mock Provider
    - Quidax Provider
    - Binance Provider
    - Coinbase Provider

    Every provider must expose the same API so
    the rest of TradeFlow never cares where
    market data comes from.
    """

    @abstractmethod
    def get_price(
        self,
        symbol: str,
    ) -> Decimal:
        """
        Returns the latest price for a symbol.
        """
        raise NotImplementedError

    @abstractmethod
    def get_supported_symbols(
        self,
    ) -> list[str]:
        """
        Returns every supported trading symbol.
        """
        raise NotImplementedError