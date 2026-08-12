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

    # Net asset quantity recorded in the portfolio.
    #
    # BUY:
    #     net cryptocurrency received after base-asset fee.
    #
    # SELL:
    #     cryptocurrency quantity actually sold.
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(32, 18),
        nullable=False,
    )

    # Weighted-average execution price.
    price: Mapped[Decimal] = mapped_column(
        Numeric(32, 8),
        nullable=False,
    )

    # Gross quote-currency execution value.
    #
    # Example:
    #     BTC 0.000015 × NGN 88,727,534
    #     = NGN 1,330.91301
    total_value: Mapped[Decimal] = mapped_column(
        Numeric(32, 8),
        nullable=False,
    )

    # Actual trading fee.
    fee: Mapped[Decimal] = mapped_column(
        Numeric(32, 18),
        nullable=False,
        default=Decimal("0"),
    )

    # Currency in which the trading fee was charged.
    #
    # BUY:
    #     normally BTC
    #
    # SELL:
    #     normally NGN
    fee_currency: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="NGN",
    )

    # Net value after fee where the fee is expressed
    # in the quote currency.
    #
    # SELL:
    #     gross NGN - NGN fee
    #
    # BUY:
    #     gross quote amount spent.
    #
    # For BUY transactions where the fee is charged
    # in the base asset, the fee is represented through
    # quantity and fee; net_value remains the quote
    # amount spent.
    net_value: Mapped[Decimal] = mapped_column(
        Numeric(32, 8),
        nullable=False,
        default=Decimal("0"),
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