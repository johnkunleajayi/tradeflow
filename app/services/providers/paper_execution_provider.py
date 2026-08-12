from decimal import Decimal

from app.core.settings import settings
from app.services.providers.execution_provider import ExecutionProvider


class PaperExecutionProvider(ExecutionProvider):
    """
    Paper-trading execution provider.

    This provider does not communicate with an exchange.

    It mirrors the current Quidax spot-market fee model:

    BUY:
        - The requested quote amount is spent.
        - The 0.1% trading fee reduces the crypto received.

    SELL:
        - The requested crypto quantity is sold.
        - The 0.1% trading fee is deducted from quote proceeds.

    PortfolioService remains responsible for updating
    the local wallet, holdings, and trade records.
    """

    @property
    def fee_rate(self) -> Decimal:
        return settings.QUIDAX_TRADING_FEE_RATE

    def buy(
        self,
        symbol: str,
        amount: Decimal,
        price: Decimal,
    ) -> dict:
        """
        Simulates a BUY execution.

        `amount` is the quote currency amount to spend.

        The fee is charged against the acquired asset.
        """

        symbol = symbol.upper()

        if amount <= 0:
            raise ValueError(
                "Buy amount must be greater than zero."
            )

        if price <= 0:
            raise ValueError(
                "Buy price must be greater than zero."
            )

        gross_quantity = amount / price

        fee = gross_quantity * self.fee_rate

        net_quantity = gross_quantity - fee

        if net_quantity <= 0:
            raise ValueError(
                "Calculated buy quantity after fee is not positive."
            )

        return {
            "symbol": symbol,
            "side": "BUY",
            "amount": amount,
            "gross_amount": amount,
            "net_amount": amount,
            "price": price,
            "quantity": net_quantity,
            "gross_quantity": gross_quantity,
            "fee": fee,
            "fee_currency": symbol,
            "fee_rate": self.fee_rate,
        }

    def sell(
        self,
        symbol: str,
        quantity: Decimal,
        price: Decimal,
    ) -> dict:
        """
        Simulates a SELL execution.

        `quantity` is the crypto quantity sold.

        The fee is deducted from quote currency proceeds.
        """

        symbol = symbol.upper()

        if quantity <= 0:
            raise ValueError(
                "Sell quantity must be greater than zero."
            )

        if price <= 0:
            raise ValueError(
                "Sell price must be greater than zero."
            )

        gross_amount = quantity * price

        fee = gross_amount * self.fee_rate

        net_amount = gross_amount - fee

        if net_amount <= 0:
            raise ValueError(
                "Calculated sell proceeds after fee are not positive."
            )

        return {
            "symbol": symbol,
            "side": "SELL",
            "amount": net_amount,
            "gross_amount": gross_amount,
            "net_amount": net_amount,
            "price": price,
            "quantity": quantity,
            "fee": fee,
            "fee_currency": "NGN",
            "fee_rate": self.fee_rate,
        }