from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.trade import Trade
from app.models.wallet import Wallet
from app.repositories.trade_repository import TradeRepository
from app.repositories.wallet_repository import WalletRepository
from app.schemas.trade import (
    BuyTradeResponse,
    SellTradeResponse,
)
from app.services.wallet_service import WalletService


class PortfolioService:
    """
    Handles TradeFlow's local trade history.

    For the LIVE trading MVP, Quidax is the sole source of truth
    for cash and cryptocurrency balances.

    This service does NOT maintain or modify local financial
    balances or holdings for live trading.

    Responsibilities:
    - Resolve the TradeFlow wallet record used for trade history.
    - Record completed trade executions.
    - Return trade execution responses.

    Quidax is responsible for:
    - Available NGN balance.
    - Available cryptocurrency balances.
    - Actual exchange-side holdings.
    - Completed exchange execution.
    """

    def __init__(
        self,
        db: Session,
    ):
        self.db = db

        self.wallet_repository = WalletRepository(
            db
        )

        self.trade_repository = TradeRepository(
            db
        )

        self.wallet_service = WalletService(
            db
        )

    def get_active_wallet(self) -> Wallet:
        """
        Returns the active TradeFlow wallet record.

        The wallet record is retained only so that local trade
        history has a wallet_id relationship.

        Its cash_balance is NOT used as the source of truth
        for LIVE trading.
        """

        wallet = (
            self.wallet_repository.get_active_wallet()
        )

        if wallet is not None:
            return wallet

        wallet = self.wallet_service.get_wallet()

        if wallet is None:
            raise RuntimeError(
                "Unable to resolve the active TradeFlow wallet."
            )

        return wallet

    def record_trade(
        self,
        wallet: Wallet,
        symbol: str,
        side: str,
        quantity: Decimal,
        price: Decimal,
        total_value: Decimal,
        fee: Decimal = Decimal("0"),
        fee_currency: str = "NGN",
        net_value: Decimal | None = None,
    ) -> Trade:
        """
        Records the actual completed exchange execution.

        This creates a historical TradeFlow record only.

        It does not modify local cash or cryptocurrency
        balances.
        """

        if quantity <= 0:
            raise ValueError(
                "Trade quantity must be greater than zero."
            )

        if price <= 0:
            raise ValueError(
                "Trade price must be greater than zero."
            )

        if total_value <= 0:
            raise ValueError(
                "Trade total value must be greater than zero."
            )

        if fee < 0:
            raise ValueError(
                "Trade fee cannot be negative."
            )

        if net_value is None:
            net_value = total_value

        if net_value < 0:
            raise ValueError(
                "Trade net value cannot be negative."
            )

        trade = Trade(
            wallet_id=wallet.id,
            symbol=symbol.upper(),
            side=side.upper(),
            quantity=quantity,
            price=price,
            total_value=total_value,
            fee=fee,
            fee_currency=fee_currency.upper(),
            net_value=net_value,
        )

        self.trade_repository.save(
            trade
        )

        return trade

    def execute_buy(
        self,
        symbol: str,
        amount: Decimal,
        price: Decimal,
        quantity: Decimal,
        gross_quantity: Decimal | None = None,
        fee: Decimal = Decimal("0"),
        fee_currency: str = "NGN",
        net_value: Decimal | None = None,
        live_execution: bool = False,
    ) -> BuyTradeResponse:
        """
        Records a completed BUY.

        LIVE mode:
            Quidax is authoritative for the actual transaction.
            TradeFlow records the completed execution only.

        PAPER mode:
            The current MVP does not maintain local financial
            balances here. Paper trading can be reintroduced
            later as a separate simulation layer.
        """

        if amount <= 0:
            raise ValueError(
                "Trade amount must be greater than zero."
            )

        if quantity <= 0:
            raise ValueError(
                "Trade quantity must be greater than zero."
            )

        wallet = self.get_active_wallet()

        if gross_quantity is None:
            gross_quantity = quantity + fee

        if net_value is None:
            net_value = amount

        try:
            trade = self.record_trade(
                wallet=wallet,
                symbol=symbol,
                side="BUY",
                quantity=quantity,
                price=price,
                total_value=amount,
                fee=fee,
                fee_currency=fee_currency,
                net_value=net_value,
            )

            self.db.commit()

            self.db.refresh(
                trade
            )

            return BuyTradeResponse(
                symbol=symbol.upper(),
                amount=amount,
                price=price,
                quantity=quantity,
                gross_quantity=gross_quantity,
                fee=fee,
                fee_currency=fee_currency.upper(),
                net_value=net_value,
            )

        except Exception:
            self.db.rollback()
            raise

    def execute_sell(
        self,
        symbol: str,
        quantity: Decimal,
        price: Decimal,
        gross_amount: Decimal | None = None,
        fee: Decimal = Decimal("0"),
        fee_currency: str = "NGN",
        net_amount: Decimal | None = None,
        live_execution: bool = False,
    ) -> SellTradeResponse:
        """
        Records a completed SELL.

        LIVE mode:
            Quidax is authoritative for the actual transaction.
            TradeFlow records the completed execution only.

        No local holding is checked or reduced.

        No local cash balance is increased.
        """

        if quantity <= 0:
            raise ValueError(
                "Sell quantity must be greater than zero."
            )

        if price <= 0:
            raise ValueError(
                "Sell price must be greater than zero."
            )

        wallet = self.get_active_wallet()

        try:
            if gross_amount is None:
                gross_amount = (
                    quantity * price
                )

            if net_amount is None:
                net_amount = (
                    gross_amount - fee
                )

            if gross_amount <= 0:
                raise ValueError(
                    "Gross sell amount must be greater than zero."
                )

            if fee < 0:
                raise ValueError(
                    "Sell fee cannot be negative."
                )

            if net_amount <= 0:
                raise ValueError(
                    "Net sell proceeds must be greater than zero."
                )

            trade = self.record_trade(
                wallet=wallet,
                symbol=symbol,
                side="SELL",
                quantity=quantity,
                price=price,
                total_value=gross_amount,
                fee=fee,
                fee_currency=fee_currency,
                net_value=net_amount,
            )

            self.db.commit()

            self.db.refresh(
                trade
            )

            return SellTradeResponse(
                symbol=symbol.upper(),
                amount=net_amount,
                gross_amount=gross_amount,
                price=price,
                quantity=quantity,
                fee=fee,
                fee_currency=fee_currency.upper(),
                net_value=net_amount,
            )

        except Exception:
            self.db.rollback()
            raise