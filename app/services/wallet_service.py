from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.constants import WalletType
from app.models.wallet import Wallet


class WalletService:
    """Handles wallet-related business logic."""

    def __init__(self, db: Session):
        self.db = db

    def get_wallet(self) -> Wallet:
        """
        Returns the active wallet.
        If none exists, creates the default paper wallet.
        """

        wallet = (
            self.db.query(Wallet)
            .filter(Wallet.is_active.is_(True))
            .first()
        )

        if wallet:
            return wallet

        wallet = Wallet(
            name="Paper Wallet",
            wallet_type=WalletType.PAPER,
            cash_balance=Decimal("100000.00"),
            is_active=True,
        )

        self.db.add(wallet)
        self.db.commit()
        self.db.refresh(wallet)

        return wallet