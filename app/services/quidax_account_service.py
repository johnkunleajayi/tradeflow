from decimal import Decimal

from app.integrations.quidax.client import QuidaxClient
from app.schemas.quidax import (
    QuidaxBalanceResponse,
    QuidaxBalancesResponse,
)


class QuidaxAccountService:
    """
    Provides read-only access to the authenticated Quidax account.

    This service does not execute trades.

    Responsibilities:
    - Retrieve live Quidax wallet balances.
    - Convert Quidax numeric values to Decimal.
    - Return API-safe balance objects.

    TradeFlow's local Paper Wallet remains completely separate.
    """

    SUPPORTED_CURRENCIES = (
        "ngn",
        "btc",
        "eth",
        "sol",
    )

    def __init__(
        self,
        client: QuidaxClient | None = None,
    ):
        self.client = client or QuidaxClient()

    @staticmethod
    def _to_decimal(
        value: object,
    ) -> Decimal:
        """
        Safely converts a Quidax numeric value to Decimal.
        """

        try:
            return Decimal(str(value))
        except Exception as exc:
            raise ValueError(
                f"Invalid Quidax balance value: {value!r}"
            ) from exc

    def _get_wallet(
        self,
        currency: str,
    ) -> dict:
        """
        Retrieves one live Quidax wallet.
        """

        response = self.client.get(
            f"/users/me/wallets/{currency}",
            authenticated=True,
        )

        data = response.get("data")

        if not isinstance(data, dict):
            raise RuntimeError(
                "Quidax wallet endpoint returned invalid data "
                f"for currency {currency.upper()}."
            )

        return data

    def get_balances(self) -> QuidaxBalancesResponse:
        """
        Retrieves live Quidax balances.

        No local database state is used.

        The values returned here come directly from Quidax.
        """

        balances: list[QuidaxBalanceResponse] = []

        for currency in self.SUPPORTED_CURRENCIES:
            wallet = self._get_wallet(currency)

            actual_currency = str(
                wallet.get(
                    "currency",
                    currency,
                )
            ).upper()

            balances.append(
                QuidaxBalanceResponse(
                    currency=actual_currency,
                    balance=self._to_decimal(
                        wallet.get(
                            "balance",
                            "0",
                        )
                    ),
                    locked=self._to_decimal(
                        wallet.get(
                            "locked",
                            "0",
                        )
                    ),
                    staked=self._to_decimal(
                        wallet.get(
                            "staked",
                            "0",
                        )
                    ),
                )
            )

        return QuidaxBalancesResponse(
            balances=balances
        )