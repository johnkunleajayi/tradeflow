from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.trade import Trade
from app.schemas.trade import (
    BuyTradeResponse,
    SellTradeResponse,
)
from app.services.portfolio_service import PortfolioService
from app.services.providers.execution_factory import ExecutionFactory
from app.services.providers.provider_factory import ProviderFactory


class TradeService:
    """
    Handles trade-related business logic.

    TradeFlow separates:

        MarketProvider
            ↓
        current market information

        ExecutionProvider
            ↓
        actual exchange execution

        PortfolioService
            ↓
        local wallet / holdings / trade records
    """

    def __init__(self, db: Session):
        self.db = db

        self.portfolio_service = PortfolioService(db)

        self.market_provider = ProviderFactory.create()

        self.execution_provider = ExecutionFactory.create()

    def get_trades(self) -> list[Trade]:
        """
        Returns all recorded trades.
        """

        return self.db.query(Trade).all()

    def buy(
        self,
        symbol: str,
        amount: Decimal,
    ) -> BuyTradeResponse:
        """
        Executes a BUY transaction.

        Flow:

            1. Normalize symbol.
            2. Validate amount.
            3. Get current market price.
            4. Validate wallet balance.
            5. Execute through provider.
            6. Receive actual execution details.
            7. Persist actual execution + fee.

        Important:

        The market price is used only as pre-trade market
        information and for compatibility with the execution
        provider interface.

        The execution provider remains authoritative for:

            - executed quantity
            - executed price
            - actual amount
            - fee
            - fee currency
            - net amount
        """

        symbol = symbol.upper()

        if amount <= 0:
            raise ValueError(
                "Buy amount must be greater than zero."
            )

        # Obtain current market information before execution.
        price = self.market_provider.get_price(symbol)

        wallet = self.portfolio_service.get_active_wallet()

        # Validate the requested maximum cash exposure
        # before sending the order to the exchange.
        self.portfolio_service.validate_cash_balance(
            wallet,
            amount,
        )

        execution = self.execution_provider.buy(
            symbol=symbol,
            amount=amount,
            price=price,
        )

        return self.portfolio_service.execute_buy(
            symbol=execution["symbol"],
            amount=execution["amount"],
            price=execution["price"],
            quantity=execution["quantity"],
            gross_quantity=execution.get(
                "gross_quantity",
                execution["quantity"],
            ),
            fee=execution.get(
                "fee",
                Decimal("0"),
            ),
            fee_currency=execution.get(
                "fee_currency",
                "NGN",
            ),
            net_value=execution.get(
                "net_amount",
                execution["amount"],
            ),
        )

    def sell(
        self,
        symbol: str,
        quantity: Decimal,
    ) -> SellTradeResponse:
        """
        Executes a SELL transaction.

        Flow:

            1. Normalize symbol.
            2. Validate quantity.
            3. Get current market price.
            4. Validate holding.
            5. Execute through provider.
            6. Receive actual execution details.
            7. Persist actual execution + fee.

        Important:

        The requested quantity is the maximum quantity the user
        intends to sell.

        The execution provider remains authoritative for:

            - actual executed quantity
            - executed price
            - gross proceeds
            - fee
            - fee currency
            - net proceeds
        """

        symbol = symbol.upper()

        if quantity <= 0:
            raise ValueError(
                "Sell quantity must be greater than zero."
            )

        # Obtain current market information before execution.
        price = self.market_provider.get_price(symbol)

        wallet = self.portfolio_service.get_active_wallet()

        holding = self.portfolio_service.get_holding_for_sell(
            wallet,
            symbol,
        )

        # Validate the requested quantity before sending
        # the order to Quidax.
        self.portfolio_service.validate_holding_quantity(
            holding,
            quantity,
        )

        execution = self.execution_provider.sell(
            symbol=symbol,
            quantity=quantity,
            price=price,
        )

        return self.portfolio_service.execute_sell(
            symbol=execution["symbol"],
            quantity=execution["quantity"],
            price=execution["price"],
            gross_amount=execution.get(
                "gross_amount",
                execution["amount"],
            ),
            fee=execution.get(
                "fee",
                Decimal("0"),
            ),
            fee_currency=execution.get(
                "fee_currency",
                "NGN",
            ),
            net_amount=execution.get(
                "net_amount",
                execution["amount"],
            ),
        )