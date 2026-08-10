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

        The current paper implementation obtains the market
        price from the configured MarketProvider and delegates
        execution to the configured ExecutionProvider.
        """

        symbol = symbol.upper()

        price = self.market_provider.get_price(symbol)

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

        The current paper implementation obtains the market
        price from the configured MarketProvider and delegates
        execution to the configured ExecutionProvider.
        """

        symbol = symbol.upper()

        price = self.market_provider.get_price(symbol)

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