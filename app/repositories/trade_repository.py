from sqlalchemy.orm import Session

from app.models.trade import Trade


class TradeRepository:
    """
    Repository responsible for trade database operations.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> list[Trade]:
        """
        Returns all trades.
        """

        return self.db.query(Trade).all()

    def get_by_id(
        self,
        trade_id: int,
    ) -> Trade | None:
        """
        Returns a trade by its ID.
        """

        return (
            self.db.query(Trade)
            .filter(Trade.id == trade_id)
            .first()
        )

    def save(
        self,
        trade: Trade,
    ) -> Trade:
        """
        Persists a trade.
        """

        self.db.add(trade)
        return trade