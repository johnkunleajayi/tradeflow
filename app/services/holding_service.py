from app.schemas.holding import HoldingResponse
from app.services.quidax_account_service import (
    QuidaxAccountService,
)


class HoldingService:
    """
    Provides live cryptocurrency holdings.

    Quidax is the sole source of truth for cryptocurrency
    balances.

    The database session is accepted for compatibility with
    the existing API dependency pattern, but it is not used.
    """

    SUPPORTED_CRYPTOCURRENCIES = {
        "BTC",
        "ETH",
        "SOL",
    }

    def __init__(self, db=None):
        self.quidax_account_service = (
            QuidaxAccountService()
        )

    def get_holdings(self) -> list[HoldingResponse]:
        """
        Returns the available live cryptocurrency balances
        from Quidax.
        """

        balances_response = (
            self.quidax_account_service.get_balances()
        )

        holdings: list[HoldingResponse] = []

        for balance in balances_response.balances:
            currency = balance.currency.upper()

            if currency not in self.SUPPORTED_CRYPTOCURRENCIES:
                continue

            available_balance = (
                balance.balance - balance.locked
            )

            if available_balance <= 0:
                continue

            holdings.append(
                HoldingResponse(
                    symbol=currency,
                    quantity=available_balance,
                )
            )

        return holdings