from decimal import Decimal

from sqlalchemy.orm import Session

from app.schemas.portfolio import (
    PortfolioAssetResponse,
    PortfolioResponse,
)
from app.services.providers.provider_factory import ProviderFactory
from app.services.quidax_account_service import (
    QuidaxAccountService,
)


class PortfolioQueryService:
    """
    Provides live portfolio read operations.

    For the LIVE MVP, Quidax is the sole source of truth
    for account balances.

    This service does not use the local Wallet or Holding
    records to determine portfolio balances.

    Responsibilities:
    - Retrieve live Quidax balances.
    - Retrieve current market prices.
    - Calculate crypto market values.
    - Calculate total portfolio value.

    This service NEVER modifies portfolio data.
    """

    def __init__(self, db: Session):
        self.db = db

        self.market_provider = ProviderFactory.create()

        self.quidax_account_service = (
            QuidaxAccountService()
        )

    def get_portfolio(self) -> PortfolioResponse:
        """
        Returns the current live portfolio summary.

        Quidax provides the actual account balances.

        Current market prices are used to calculate the
        NGN value of cryptocurrency balances.
        """

        balances_response = (
            self.quidax_account_service.get_balances()
        )

        cash_balance = Decimal("0")

        assets: list[PortfolioAssetResponse] = []

        holdings_value = Decimal("0")

        for balance in balances_response.balances:
            currency = balance.currency.upper()

            available_balance = (
                balance.balance - balance.locked
            )

            if available_balance < 0:
                available_balance = Decimal("0")

            if currency == "NGN":
                cash_balance = available_balance
                continue

            if currency not in {"BTC", "ETH", "SOL"}:
                continue

            if available_balance <= 0:
                continue

            current_price = (
                self.market_provider.get_price(
                    currency
                )
            )

            market_value = (
                available_balance * current_price
            )

            holdings_value += market_value

            assets.append(
                PortfolioAssetResponse(
                    symbol=currency,
                    quantity=available_balance,
                    average_buy_price=None,
                    current_price=current_price,
                    market_value=market_value,
                )
            )

        total_portfolio_value = (
            cash_balance + holdings_value
        )

        return PortfolioResponse(
            cash_balance=cash_balance,
            holdings_value=holdings_value,
            total_portfolio_value=total_portfolio_value,
            assets=assets,
        )