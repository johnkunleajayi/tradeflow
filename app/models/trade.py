from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    wallet_id: Mapped[int] = mapped_column(
        ForeignKey("wallets.id"),
        nullable=False,
    )

    symbol: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )

    side: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    quantity: Mapped[Decimal] = mapped_column(
        Numeric(24, 8),
        nullable=False,
    )

    price: Mapped[Decimal] = mapped_column(
        Numeric(24, 2),
        nullable=False,
    )

    total_value: Mapped[Decimal] = mapped_column(
        Numeric(24, 2),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    wallet = relationship(
        "Wallet",
        back_populates="trades",
    )