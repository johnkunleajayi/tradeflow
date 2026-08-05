from sqlalchemy.orm import Session

from app.models.holding import Holding


class HoldingRepository:
    """
    Repository responsible for holding database operations.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_by_wallet_and_symbol(
        self,
        wallet_id: int,
        symbol: str,
    ) -> Holding | None:
        """
        Returns a holding for a wallet and symbol.
        """

        return (
            self.db.query(Holding)
            .filter(
                Holding.wallet_id == wallet_id,
                Holding.symbol == symbol.upper(),
            )
            .first()
        )

    def save(
        self,
        holding: Holding,
    ) -> Holding:
        """
        Persists a holding.
        """

        self.db.add(holding)
        return holding

    def delete(
        self,
        holding: Holding,
    ) -> None:
        """
        Deletes a holding.
        """

        self.db.delete(holding)