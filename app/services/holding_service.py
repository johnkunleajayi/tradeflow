from sqlalchemy.orm import Session

from app.models.holding import Holding


class HoldingService:
    """Handles holding-related business logic."""

    def __init__(self, db: Session):
        self.db = db

    def get_holdings(self) -> list[Holding]:
        """
        Returns all crypto holdings.
        """

        return self.db.query(Holding).all()