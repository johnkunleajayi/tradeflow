from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.trade import Trade
from app.schemas.trade import (
    BuyTradeResponse,
    SellTradeResponse,
)
from app.services.portfolio_service import PortfolioService
from app.services.providers.provider_factory import (
    ProviderFactory,
)


class TradeService:
    """Handles trade-related business logic."""

    def __init__(self, db: Session):
        self.db = db
        self.portfolio_service = PortfolioService(db)
        self.market_provider = ProviderFactory.create()

    def get_trades(self) -> list[Trade]:
        """
        Returns all trades.
        """

        return self.db.query(Trade).all()

    def buy(
        self,
        symbol: str,
        amount: Decimal,
    ) -> BuyTradeResponse:
        """
        Executes a paper BUY trade.
        """

        symbol = symbol.upper()

        price = self.market_provider.get_price(symbol)

        quantity = amount / price

        return self.portfolio_service.execute_buy(
            symbol=symbol,
            amount=amount,
            price=price,
            quantity=quantity,
        )

    def sell(
        self,
        symbol: str,
        quantity: Decimal,
    ) -> SellTradeResponse:
        """
        Executes a paper SELL trade.
        """

        symbol = symbol.upper()

        price = self.market_provider.get_price(symbol)

        return self.portfolio_service.execute_sell(
            symbol=symbol,
            quantity=quantity,
            price=price,
        )