from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.exceptions import (
    HoldingNotFoundError,
    InsufficientBalanceError,
    InsufficientHoldingError,
    WalletNotFoundError,
)
from app.models.holding import Holding
from app.models.trade import Trade
from app.models.wallet import Wallet
from app.repositories.holding_repository import HoldingRepository
from app.repositories.trade_repository import TradeRepository
from app.repositories.wallet_repository import WalletRepository
from app.schemas.trade import BuyTradeResponse, SellTradeResponse
from app.services.wallet_service import WalletService


class PortfolioService:
    """
    Handles local portfolio state.

    Responsibilities:
    - Active wallet
    - Cash balance
    - Holdings
    - Portfolio updates
    - Trade recording

    This service does NOT communicate with Quidax.

    For live trading, the execution provider is responsible for
    obtaining the actual execution details from the exchange.
    This service then records those actual execution details.
    """

    def __init__(self, db: Session):
        self.db = db

        self.wallet_repository = WalletRepository(db)
        self.holding_repository = HoldingRepository(db)
        self.trade_repository = TradeRepository(db)

        self.wallet_service = WalletService(db)

    def get_active_wallet(self) -> Wallet:
        """
        Returns the active wallet.

        If no active wallet exists, WalletService creates or
        returns the default wallet.
        """

        wallet = self.wallet_repository.get_active_wallet()

        if wallet is not None:
            return wallet

        wallet = self.wallet_service.get_wallet()

        if wallet is None:
            raise WalletNotFoundError()

        return wallet

    def validate_cash_balance(
        self,
        wallet: Wallet,
        amount: Decimal,
    ) -> None:
        """
        Ensures the wallet has sufficient cash.
        """

        if amount <= 0:
            raise ValueError(
                "Trade amount must be greater than zero."
            )

        if wallet.cash_balance < amount:
            raise InsufficientBalanceError()

    def deduct_cash(
        self,
        wallet: Wallet,
        amount: Decimal,
    ) -> Wallet:
        """
        Deducts the actual executed cash value from the wallet.
        """

        if amount <= 0:
            raise ValueError(
                "Cash deduction amount must be greater than zero."
            )

        if wallet.cash_balance < amount:
            raise InsufficientBalanceError()

        wallet.cash_balance -= amount

        self.wallet_repository.save(wallet)

        return wallet

    def add_cash(
        self,
        wallet: Wallet,
        amount: Decimal,
    ) -> Wallet:
        """
        Adds actual executed cash proceeds to the wallet.
        """

        if amount <= 0:
            raise ValueError(
                "Cash addition amount must be greater than zero."
            )

        wallet.cash_balance += amount

        self.wallet_repository.save(wallet)

        return wallet

    def create_or_update_holding(
        self,
        wallet: Wallet,
        symbol: str,
        quantity: Decimal,
        price: Decimal,
    ) -> Holding:
        """
        Creates a new holding or updates an existing holding.

        The supplied quantity and price must represent the
        ACTUAL completed execution.
        """

        if quantity <= 0:
            raise ValueError(
                "Holding quantity must be greater than zero."
            )

        if price <= 0:
            raise ValueError(
                "Holding price must be greater than zero."
            )

        symbol = symbol.upper()

        holding = (
            self.holding_repository.get_by_wallet_and_symbol(
                wallet.id,
                symbol,
            )
        )

        if holding is None:
            holding = Holding(
                wallet_id=wallet.id,
                symbol=symbol,
                quantity=quantity,
                average_buy_price=price,
            )

            self.holding_repository.save(holding)

            return holding

        total_quantity = holding.quantity + quantity

        total_cost = (
            holding.quantity * holding.average_buy_price
        ) + (
            quantity * price
        )

        holding.average_buy_price = (
            total_cost / total_quantity
        )

        holding.quantity = total_quantity

        self.holding_repository.save(holding)

        return holding

    def get_holding_for_sell(
        self,
        wallet: Wallet,
        symbol: str,
    ) -> Holding:
        """
        Gets the holding required for a SELL.
        """

        holding = (
            self.holding_repository.get_by_wallet_and_symbol(
                wallet.id,
                symbol,
            )
        )

        if holding is None:
            raise HoldingNotFoundError(symbol)

        return holding

    def validate_holding_quantity(
        self,
        holding: Holding,
        quantity: Decimal,
    ) -> None:
        """
        Ensures enough asset is available for the requested SELL.
        """

        if quantity <= 0:
            raise ValueError(
                "Sell quantity must be greater than zero."
            )

        if holding.quantity < quantity:
            raise InsufficientHoldingError(
                holding.symbol
            )

    def reduce_holding(
        self,
        holding: Holding,
        quantity: Decimal,
    ) -> Holding | None:
        """
        Reduces the holding by the ACTUAL executed quantity.

        If the remaining quantity is zero, the holding is deleted.
        """

        if quantity <= 0:
            raise ValueError(
                "Holding reduction quantity must be greater than zero."
            )

        if holding.quantity < quantity:
            raise InsufficientHoldingError(
                holding.symbol
            )

        holding.quantity -= quantity

        if holding.quantity <= 0:
            self.holding_repository.delete(holding)
            return None

        self.holding_repository.save(holding)

        return holding

    def record_trade(
        self,
        wallet: Wallet,
        symbol: str,
        side: str,
        quantity: Decimal,
        price: Decimal,
    ) -> Trade:
        """
        Records the ACTUAL completed exchange execution.
        """

        if quantity <= 0:
            raise ValueError(
                "Trade quantity must be greater than zero."
            )

        if price <= 0:
            raise ValueError(
                "Trade price must be greater than zero."
            )

        trade = Trade(
            wallet_id=wallet.id,
            symbol=symbol.upper(),
            side=side.upper(),
            quantity=quantity,
            price=price,
            total_value=quantity * price,
        )

        self.trade_repository.save(trade)

        return trade

    def execute_buy(
        self,
        symbol: str,
        amount: Decimal,
        price: Decimal,
        quantity: Decimal,
    ) -> BuyTradeResponse:
        """
        Records a completed BUY using the ACTUAL execution.

        `amount`, `price`, and `quantity` should come from the
        execution provider after Quidax confirms the order.

        The local wallet is charged the actual execution value,
        not the original estimated order value.
        """

        wallet = self.get_active_wallet()

        self.validate_cash_balance(
            wallet,
            amount,
        )

        try:
            self.deduct_cash(
                wallet,
                amount,
            )

            self.create_or_update_holding(
                wallet=wallet,
                symbol=symbol,
                quantity=quantity,
                price=price,
            )

            trade = self.record_trade(
                wallet=wallet,
                symbol=symbol,
                side="BUY",
                quantity=quantity,
                price=price,
            )

            self.db.commit()

            self.db.refresh(wallet)
            self.db.refresh(trade)

            return BuyTradeResponse(
                symbol=symbol.upper(),
                amount=amount,
                price=price,
                quantity=quantity,
            )

        except Exception:
            self.db.rollback()
            raise

    def execute_sell(
        self,
        symbol: str,
        quantity: Decimal,
        price: Decimal,
    ) -> SellTradeResponse:
        """
        Records a completed SELL using the ACTUAL execution.

        `quantity` and `price` should come from the execution
        provider after Quidax confirms the order.

        The wallet receives the actual executed value.
        """

        wallet = self.get_active_wallet()

        try:
            holding = self.get_holding_for_sell(
                wallet,
                symbol,
            )

            self.validate_holding_quantity(
                holding,
                quantity,
            )

            total_value = quantity * price

            self.reduce_holding(
                holding,
                quantity,
            )

            self.add_cash(
                wallet,
                total_value,
            )

            trade = self.record_trade(
                wallet=wallet,
                symbol=symbol,
                side="SELL",
                quantity=quantity,
                price=price,
            )

            self.db.commit()

            self.db.refresh(wallet)
            self.db.refresh(trade)

            return SellTradeResponse(
                symbol=symbol.upper(),
                amount=total_value,
                price=price,
                quantity=quantity,
            )

        except Exception:
            self.db.rollback()
            raise