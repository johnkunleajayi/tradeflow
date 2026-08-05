from sqlalchemy.orm import Session

from app.models.wallet import Wallet


class WalletRepository:
    """
    Repository responsible for wallet database operations.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_active_wallet(self) -> Wallet | None:
        """
        Returns the active wallet if one exists.
        """

        return (
            self.db.query(Wallet)
            .filter(Wallet.is_active.is_(True))
            .first()
        )

    def save(self, wallet: Wallet) -> Wallet:
        """
        Persists wallet changes.
        """

        self.db.add(wallet)
        return wallet