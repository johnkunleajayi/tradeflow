from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.settings import settings
from app.models.trade import Trade
from app.schemas.trade import (
    BuyTradeResponse,
    SellTradeResponse,
)
from app.services.portfolio_service import PortfolioService
from app.services.providers.execution_factory import ExecutionFactory
from app.services.providers.provider_factory import ProviderFactory


class TradeService:
    """
    Handles trade-related business logic.

    TradeFlow separates:

        MarketProvider
            ↓
        current market information

        ExecutionProvider
            ↓
        actual exchange execution

        PortfolioService
            ↓
        local wallet / holdings / trade records

    Trading modes:

        PAPER
            Local TradeFlow wallet and holdings are authoritative
            for pre-trade validation.

        LIVE
            Quidax is authoritative for available balances and
            actual exchange execution.

            The local portfolio is updated from the actual
            completed Quidax execution.
    """

    def __init__(self, db: Session):
        self.db = db

        self.portfolio_service = PortfolioService(db)

        self.market_provider = ProviderFactory.create()

        self.execution_provider = ExecutionFactory.create()

    @property
    def is_live(self) -> bool:
        """
        Returns True when TradeFlow is configured for live
        exchange execution.

        LIVE mode means the execution provider is responsible
        for communicating with Quidax.

        PAPER mode keeps the local TradeFlow portfolio as the
        source of truth for simulated execution.
        """

        return (
            str(
                settings.TRADING_MODE
            )
            .strip()
            .lower()
            == "live"
        )

    def get_trades(self) -> list[Trade]:
        """
        Returns all recorded trades.
        """

        return self.db.query(
            Trade
        ).all()

    def buy(
        self,
        symbol: str,
        amount: Decimal,
    ) -> BuyTradeResponse:
        """
        Executes a BUY transaction.

        PAPER mode:

            1. Normalize symbol.
            2. Validate amount.
            3. Get current market price.
            4. Validate local wallet balance.
            5. Execute through paper provider.
            6. Persist simulated execution.

        LIVE mode:

            1. Normalize symbol.
            2. Validate amount.
            3. Get current market price.
            4. DO NOT validate against the local Paper Wallet.
            5. Execute through Quidax.
            6. Receive actual execution details.
            7. Update the local portfolio from the actual
               completed exchange execution.

        In LIVE mode, Quidax is authoritative for the
        exchange-side available balance.

        The execution provider remains authoritative for:

            - executed quantity
            - executed price
            - actual amount
            - fee
            - fee currency
            - net amount
        """

        symbol = symbol.upper()

        if amount <= 0:
            raise ValueError(
                "Buy amount must be greater than zero."
            )

        # Obtain current market information before execution.
        #
        # This is informational and is also retained for
        # compatibility with the ExecutionProvider interface.
        price = self.market_provider.get_price(
            symbol
        )

        if price <= 0:
            raise ValueError(
                f"Invalid market price for {symbol}: {price}"
            )

        if not self.is_live:
            # PAPER MODE:
            #
            # The local TradeFlow wallet is authoritative.
            wallet = (
                self.portfolio_service
                .get_active_wallet()
            )

            self.portfolio_service.validate_cash_balance(
                wallet,
                amount,
            )

        # LIVE MODE:
        #
        # Do NOT validate against the local Paper Wallet.
        #
        # The Quidax execution provider is responsible for
        # executing against the real exchange account.
        execution = self.execution_provider.buy(
            symbol=symbol,
            amount=amount,
            price=price,
        )

        if not execution:
            raise RuntimeError(
                f"BUY execution returned no result for {symbol}."
            )

        execution_symbol = str(
            execution.get(
                "symbol",
                symbol,
            )
        ).upper()

        execution_amount = Decimal(
            str(
                execution.get(
                    "amount",
                    "0",
                )
            )
        )

        execution_price = Decimal(
            str(
                execution.get(
                    "price",
                    "0",
                )
            )
        )

        execution_quantity = Decimal(
            str(
                execution.get(
                    "quantity",
                    "0",
                )
            )
        )

        if execution_amount <= 0:
            raise RuntimeError(
                f"BUY execution returned invalid amount "
                f"for {execution_symbol}: "
                f"{execution_amount}"
            )

        if execution_price <= 0:
            raise RuntimeError(
                f"BUY execution returned invalid price "
                f"for {execution_symbol}: "
                f"{execution_price}"
            )

        if execution_quantity <= 0:
            raise RuntimeError(
                f"BUY execution returned invalid quantity "
                f"for {execution_symbol}: "
                f"{execution_quantity}"
            )

        return self.portfolio_service.execute_buy(
            symbol=execution_symbol,
            amount=execution_amount,
            price=execution_price,
            quantity=execution_quantity,
            gross_quantity=execution.get(
                "gross_quantity",
                execution_quantity,
            ),
            fee=execution.get(
                "fee",
                Decimal("0"),
            ),
            fee_currency=execution.get(
                "fee_currency",
                "NGN",
            ),
            net_value=execution.get(
                "net_amount",
                execution_amount,
            ),
            live_execution=self.is_live,
        )

    def sell(
        self,
        symbol: str,
        quantity: Decimal,
    ) -> SellTradeResponse:
        """
        Executes a SELL transaction.

        PAPER mode:

            1. Normalize symbol.
            2. Validate quantity.
            3. Get current market price.
            4. Validate local holding.
            5. Execute through paper provider.
            6. Persist simulated execution.

        LIVE mode:

            1. Normalize symbol.
            2. Validate quantity.
            3. Get current market price.
            4. DO NOT validate against the local holding.
            5. Execute through Quidax.
            6. Receive actual execution details.
            7. Update the local portfolio from the actual
               completed exchange execution.

        In LIVE mode, Quidax is authoritative for the
        exchange-side cryptocurrency balance.

        The execution provider remains authoritative for:

            - actual executed quantity
            - executed price
            - gross proceeds
            - fee
            - fee currency
            - net proceeds
        """

        symbol = symbol.upper()

        if quantity <= 0:
            raise ValueError(
                "Sell quantity must be greater than zero."
            )

        # Obtain current market information before execution.
        price = self.market_provider.get_price(
            symbol
        )

        if price <= 0:
            raise ValueError(
                f"Invalid market price for {symbol}: {price}"
            )

        if not self.is_live:
            # PAPER MODE:
            #
            # The local TradeFlow holding is authoritative.
            wallet = (
                self.portfolio_service
                .get_active_wallet()
            )

            holding = (
                self.portfolio_service
                .get_holding_for_sell(
                    wallet,
                    symbol,
                )
            )

            self.portfolio_service.validate_holding_quantity(
                holding,
                quantity,
            )

        # LIVE MODE:
        #
        # Do NOT validate against the local TradeFlow holding.
        #
        # The automation worker obtains the actual available
        # Quidax balance and the Quidax execution provider
        # executes against the exchange account.
        execution = self.execution_provider.sell(
            symbol=symbol,
            quantity=quantity,
            price=price,
        )

        if not execution:
            raise RuntimeError(
                f"SELL execution returned no result for {symbol}."
            )

        execution_symbol = str(
            execution.get(
                "symbol",
                symbol,
            )
        ).upper()

        execution_quantity = Decimal(
            str(
                execution.get(
                    "quantity",
                    "0",
                )
            )
        )

        execution_price = Decimal(
            str(
                execution.get(
                    "price",
                    "0",
                )
            )
        )

        execution_gross_amount = Decimal(
            str(
                execution.get(
                    "gross_amount",
                    execution.get(
                        "amount",
                        "0",
                    ),
                )
            )
        )

        execution_net_amount = Decimal(
            str(
                execution.get(
                    "net_amount",
                    execution.get(
                        "amount",
                        "0",
                    ),
                )
            )
        )

        if execution_quantity <= 0:
            raise RuntimeError(
                f"SELL execution returned invalid quantity "
                f"for {execution_symbol}: "
                f"{execution_quantity}"
            )

        if execution_price <= 0:
            raise RuntimeError(
                f"SELL execution returned invalid price "
                f"for {execution_symbol}: "
                f"{execution_price}"
            )

        if execution_gross_amount <= 0:
            raise RuntimeError(
                f"SELL execution returned invalid gross amount "
                f"for {execution_symbol}: "
                f"{execution_gross_amount}"
            )

        if execution_net_amount <= 0:
            raise RuntimeError(
                f"SELL execution returned invalid net amount "
                f"for {execution_symbol}: "
                f"{execution_net_amount}"
            )

        return self.portfolio_service.execute_sell(
            symbol=execution_symbol,
            quantity=execution_quantity,
            price=execution_price,
            gross_amount=execution_gross_amount,
            fee=execution.get(
                "fee",
                Decimal("0"),
            ),
            fee_currency=execution.get(
                "fee_currency",
                "NGN",
            ),
            net_amount=execution_net_amount,
            live_execution=self.is_live,
        )