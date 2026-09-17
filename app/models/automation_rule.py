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

    # Price movement required to trigger a new BUY.
    #
    # Example:
    #
    #     100000
    #
    # BUY trigger:
    #
    #     reference_price - price_step
    price_step: Mapped[Decimal] = mapped_column(
        Numeric(32, 8),
        nullable=False,
    )

    # Market price used as the anchor for finding
    # the next BUY opportunity.
    #
    # This is NOT the price used to determine whether
    # an open position should be sold.
    reference_price: Mapped[Decimal | None] = mapped_column(
        Numeric(32, 8),
        nullable=True,
    )

    # Indicates whether TradeFlow currently has an
    # open automated trading position for this rule.
    #
    # False:
    #     TradeFlow is waiting for a BUY opportunity.
    #
    # True:
    #     TradeFlow has an open position and must only
    #     evaluate the position's profitable SELL target.
    position_open: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Actual Quidax execution price of the automated BUY.
    #
    # This becomes the cost basis for the open position.
    entry_price: Mapped[Decimal | None] = mapped_column(
        Numeric(32, 8),
        nullable=True,
    )

    # Actual cryptocurrency quantity received from the
    # automated BUY after the configured fee model.
    #
    # This is the quantity TradeFlow should attempt to
    # sell when the profitable exit is reached.
    entry_quantity: Mapped[Decimal | None] = mapped_column(
        Numeric(32, 16),
        nullable=True,
    )

    # Actual NGN value spent on the completed BUY.
    #
    # This is used as the cost basis when calculating
    # the minimum profitable SELL price.
    entry_cost: Mapped[Decimal | None] = mapped_column(
        Numeric(32, 8),
        nullable=True,
    )

    # Minimum SELL price required to achieve the configured
    # AUTOMATION_MIN_PROFIT after estimated trading fees.
    #
    # This is calculated when the BUY completes.
    target_sell_price: Mapped[Decimal | None] = mapped_column(
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