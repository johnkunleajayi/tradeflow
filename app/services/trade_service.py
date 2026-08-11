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

    TradeService coordinates:

    - Market price retrieval
    - Pre-trade portfolio validation
    - Trade execution
    - Portfolio updates
    - Trade history

    Market data and trade execution are deliberately separated.

    MarketProvider answers:
        "What is the current market price?"

    ExecutionProvider answers:
        "How should this trade be executed?"

    PortfolioService answers:
        "How should the local portfolio state be updated?"
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
            2. Validate requested amount.
            3. Retrieve current market price.
            4. Validate available wallet balance.
            5. Send order to configured execution provider.
            6. Receive actual execution details.
            7. Record actual execution in the portfolio.

        The execution provider remains authoritative for the
        final executed quantity and price.
        """

        symbol = symbol.upper()

        if amount <= 0:
            raise ValueError(
                "Buy amount must be greater than zero."
            )

        price = self.market_provider.get_price(symbol)

        wallet = self.portfolio_service.get_active_wallet()

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
            2. Validate requested quantity.
            3. Retrieve current market price.
            4. Validate available holding.
            5. Send order to configured execution provider.
            6. Receive actual execution details.
            7. Record actual execution in the portfolio.

        The execution provider remains authoritative for the
        final executed quantity and price.
        """

        symbol = symbol.upper()

        if quantity <= 0:
            raise ValueError(
                "Sell quantity must be greater than zero."
            )

        price = self.market_provider.get_price(symbol)

        wallet = self.portfolio_service.get_active_wallet()

        holding = self.portfolio_service.get_holding_for_sell(
            wallet,
            symbol,
        )

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
        )