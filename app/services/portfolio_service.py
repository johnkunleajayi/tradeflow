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
from app.schemas.trade import (
    BuyTradeResponse,
    SellTradeResponse,
)
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

    The execution provider supplies actual completed
    execution information.

    This service then applies that execution to the
    local TradeFlow portfolio.
    """

    def __init__(
        self,
        db: Session,
    ):
        self.db = db

        self.wallet_repository = WalletRepository(
            db
        )

        self.holding_repository = HoldingRepository(
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
        Returns the active wallet.

        If no active wallet exists, WalletService creates
        or returns the default wallet.
        """

        wallet = (
            self.wallet_repository.get_active_wallet()
        )

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
        Deducts actual quote-currency cash spent.
        """

        if amount <= 0:
            raise ValueError(
                "Cash deduction amount must be greater "
                "than zero."
            )

        if wallet.cash_balance < amount:
            raise InsufficientBalanceError()

        wallet.cash_balance -= amount

        self.wallet_repository.save(
            wallet
        )

        return wallet

    def add_cash(
        self,
        wallet: Wallet,
        amount: Decimal,
    ) -> Wallet:
        """
        Adds actual NET cash proceeds.
        """

        if amount <= 0:
            raise ValueError(
                "Cash addition amount must be greater "
                "than zero."
            )

        wallet.cash_balance += amount

        self.wallet_repository.save(
            wallet
        )

        return wallet

    def create_or_update_holding(
        self,
        wallet: Wallet,
        symbol: str,
        quantity: Decimal,
        price: Decimal,
    ) -> Holding:
        """
        Creates or updates a holding using the NET asset
        quantity actually received.
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
            self.holding_repository
            .get_by_wallet_and_symbol(
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

            self.holding_repository.save(
                holding
            )

            return holding

        total_quantity = (
            holding.quantity + quantity
        )

        total_cost = (
            holding.quantity
            * holding.average_buy_price
        ) + (
            quantity * price
        )

        holding.average_buy_price = (
            total_cost / total_quantity
        )

        holding.quantity = total_quantity

        self.holding_repository.save(
            holding
        )

        return holding

    def get_holding_for_sell(
        self,
        wallet: Wallet,
        symbol: str,
    ) -> Holding:
        """
        Gets the holding required for a SELL.
        """

        symbol = symbol.upper()

        holding = (
            self.holding_repository
            .get_by_wallet_and_symbol(
                wallet.id,
                symbol,
            )
        )

        if holding is None:
            raise HoldingNotFoundError(
                symbol
            )

        return holding

    def validate_holding_quantity(
        self,
        holding: Holding,
        quantity: Decimal,
    ) -> None:
        """
        Ensures enough asset is available for the
        requested SELL.
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
        Reduces the holding by the ACTUAL executed
        quantity.

        If remaining quantity is zero, the holding
        is deleted.
        """

        if quantity <= 0:
            raise ValueError(
                "Holding reduction quantity must be greater "
                "than zero."
            )

        if holding.quantity < quantity:
            raise InsufficientHoldingError(
                holding.symbol
            )

        holding.quantity -= quantity

        if holding.quantity <= 0:
            self.holding_repository.delete(
                holding
            )

            return None

        self.holding_repository.save(
            holding
        )

        return holding

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

        total_value:
            Gross execution value.

        fee:
            Actual trading fee applied to the execution.

        fee_currency:
            Currency in which the fee was charged.

        net_value:
            Net quote value after fee where applicable.
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
    ) -> BuyTradeResponse:
        """
        Records a completed BUY using actual execution
        information.

        For a BUY:

        - amount = actual quote currency spent
        - gross_quantity = cryptocurrency before fee
        - quantity = cryptocurrency actually received
        - fee = trading fee
        - fee_currency = normally base cryptocurrency
        """

        wallet = self.get_active_wallet()

        self.validate_cash_balance(
            wallet,
            amount,
        )

        if gross_quantity is None:
            gross_quantity = quantity + fee

        if net_value is None:
            net_value = amount

        try:
            # Actual quote amount spent.
            self.deduct_cash(
                wallet,
                amount,
            )

            # Net cryptocurrency received after any
            # base-asset trading fee.
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
                total_value=amount,
                fee=fee,
                fee_currency=fee_currency,
                net_value=net_value,
            )

            self.db.commit()

            self.db.refresh(
                wallet
            )

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
    ) -> SellTradeResponse:
        """
        Records a completed SELL using actual execution
        information.

        For a SELL:

        - quantity = actual cryptocurrency sold
        - gross_amount = gross quote proceeds
        - fee = actual quote-currency trading fee
        - net_amount = cash actually received
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

            # Remove the actual cryptocurrency quantity
            # filled by the exchange.
            self.reduce_holding(
                holding,
                quantity,
            )

            # Add only the actual NET quote proceeds.
            self.add_cash(
                wallet,
                net_amount,
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
                wallet
            )

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