from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class AutomationRule(Base):
    __tablename__ = "automation_rules"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    symbol: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )

    # Price movement required to trigger a trade.
    #
    # Example:
    #
    #     100000
    #
    # BUY:
    #     reference price - 100000
    #
    # SELL:
    #     reference price + 100000
    price_step: Mapped[Decimal] = mapped_column(
        Numeric(32, 8),
        nullable=False,
    )

    # Price from which the next BUY/SELL movement
    # is calculated.
    #
    # This is persisted so a server restart does not
    # silently create a new trading reference.
    reference_price: Mapped[Decimal | None] = mapped_column(
        Numeric(32, 8),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )