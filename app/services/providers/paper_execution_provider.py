from decimal import Decimal

from app.services.providers.execution_provider import ExecutionProvider


class PaperExecutionProvider(ExecutionProvider):
    """
    Paper-trading execution provider.

    This provider does not communicate with an exchange.

    It calculates the execution details that TradeFlow needs,
    while the PortfolioService remains responsible for updating
    the wallet, holdings, and trade records.
    """

    def buy(
        self,
        symbol: str,
        amount: Decimal,
        price: Decimal,
    ) -> dict:
        """
        Simulates a BUY execution.

        The requested amount is converted into an asset quantity
        using the supplied market price.
        """

        symbol = symbol.upper()

        quantity = amount / price

        return {
            "symbol": symbol,
            "side": "BUY",
            "amount": amount,
            "price": price,
            "quantity": quantity,
        }

    def sell(
        self,
        symbol: str,
        quantity: Decimal,
        price: Decimal,
    ) -> dict:
        """
        Simulates a SELL execution.

        The supplied quantity is valued using the supplied
        market price.
        """

        symbol = symbol.upper()

        amount = quantity * price

        return {
            "symbol": symbol,
            "side": "SELL",
            "amount": amount,
            "price": price,
            "quantity": quantity,
        }