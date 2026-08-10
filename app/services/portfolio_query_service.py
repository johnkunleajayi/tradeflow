from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.exceptions import WalletNotFoundError
from app.models.holding import Holding
from app.repositories.holding_repository import HoldingRepository
from app.repositories.wallet_repository import WalletRepository
from app.schemas.portfolio import (
    PortfolioAssetResponse,
    PortfolioResponse,
)
from app.services.providers.provider_factory import ProviderFactory
from app.services.wallet_service import WalletService


class PortfolioQueryService:
    """
    Provides portfolio read operations.

    Responsibilities:
    - Portfolio valuation
    - Holdings valuation
    - Dashboard data
    - Portfolio reporting

    This service NEVER modifies portfolio data.
    """

    def __init__(self, db: Session):
        self.db = db

        self.wallet_repository = WalletRepository(db)
        self.holding_repository = HoldingRepository(db)
        self.wallet_service = WalletService(db)

        self.market_provider = ProviderFactory.create()

    def get_active_wallet(self):
        """
        Returns the active wallet.

        If no wallet exists, the default Paper Wallet
        is created automatically.
        """

        wallet = self.wallet_repository.get_active_wallet()

        if wallet is not None:
            return wallet

        wallet = self.wallet_service.get_wallet()

        if wallet is None:
            raise WalletNotFoundError()

        return wallet

    def get_portfolio(self) -> PortfolioResponse:
        """
        Returns a complete portfolio summary.
        """

        wallet = self.get_active_wallet()

        holdings = (
            self.db.query(Holding)
            .filter(Holding.wallet_id == wallet.id)
            .all()
        )

        assets: list[PortfolioAssetResponse] = []

        holdings_value = Decimal("0.00")

        for holding in holdings:

            current_price = self.market_provider.get_price(
                holding.symbol
            )

            market_value = (
                holding.quantity * current_price
            )

            holdings_value += market_value

            assets.append(
                PortfolioAssetResponse(
                    symbol=holding.symbol,
                    quantity=holding.quantity,
                    average_buy_price=holding.average_buy_price,
                    current_price=current_price,
                    market_value=market_value,
                )
            )

        total_portfolio_value = (
            wallet.cash_balance + holdings_value
        )

        return PortfolioResponse(
            cash_balance=wallet.cash_balance,
            holdings_value=holdings_value,
            total_portfolio_value=total_portfolio_value,
            assets=assets,
        )