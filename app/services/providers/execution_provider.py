from abc import ABC, abstractmethod
from decimal import Decimal


class ExecutionProvider(ABC):
    """
    Contract for every trade execution provider.

    Examples:
    - PaperExecutionProvider
    - QuidaxExecutionProvider
    - BinanceExecutionProvider
    - CoinbaseExecutionProvider

    The rest of TradeFlow should not care whether a trade
    is executed against the paper portfolio or a real exchange.
    """

    @abstractmethod
    def buy(
        self,
        symbol: str,
        amount: Decimal,
        price: Decimal,
    ) -> dict:
        """
        Executes a BUY order.

        Returns execution information required by
        the trading layer, including fee information.
        """
        raise NotImplementedError

    @abstractmethod
    def sell(
        self,
        symbol: str,
        quantity: Decimal,
        price: Decimal,
    ) -> dict:
        """
        Executes a SELL order.

        Returns execution information required by
        the trading layer, including fee information.
        """
        raise NotImplementedError