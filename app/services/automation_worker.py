import logging
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.settings import settings
from app.db.database import SessionLocal
from app.models.automation_rule import AutomationRule
from app.services.automation_service import AutomationService
from app.services.market_data_service import MarketDataService
from app.services.quidax_account_service import QuidaxAccountService
from app.services.trade_service import TradeService


logger = logging.getLogger("tradeflow.automation")


class AutomationWorker:
    """
    Background worker for TradeFlow automated trading.

    Strategy:

        BUY:
            Current price <= reference price - price_step.

        SELL:
            Current price >= reference price + (price_step * 2).

    Safety behaviour:

        - Insufficient NGN for BUY:
              Skip trade safely.

        - Insufficient crypto for SELL:
              Skip trade safely.

        - Quidax/API execution failure:
              Log the failure and keep the worker alive.

        - Successful trade:
              Move the automation reference price to the
              actual execution price.

        - Skipped/failed trade:
              Keep the existing reference price.

    The worker never owns exchange execution logic.
    TradeService remains responsible for actual BUY/SELL execution.

    The worker deliberately does not hardcode trade amounts.

    BUY:
        Uses the currently available NGN balance.

    SELL:
        Uses the currently available balance of the
        cryptocurrency being traded.

    Quidax precision normalization remains the responsibility
    of QuidaxExecutionProvider.

    LIVE TRADING SAFETY:

        By default, the worker runs in SAFE/DRY-RUN mode.

        When a trigger is detected, it will:

            - retrieve the real Quidax balance
            - calculate the actual dynamic amount/quantity
            - log the intended trade

        But it will NOT send the order to Quidax unless:

            AUTOMATION_LIVE_TRADING=true

        is explicitly configured.

        This prevents the automation worker from accidentally
        executing a real trade while the strategy is being tested.
    """

    def __init__(self):
        self.market_data_service = MarketDataService()

        self.quidax_account_service = (
            QuidaxAccountService()
        )

        self.running = False

    @property
    def poll_interval(self) -> float:
        """
        Number of seconds between market checks.
        """

        return max(
            float(
                getattr(
                    settings,
                    "AUTOMATION_POLL_INTERVAL",
                    5,
                )
            ),
            1,
        )

    @property
    def live_trading_enabled(self) -> bool:
        """
        Determines whether the automation worker is allowed
        to submit real orders to Quidax.

        SAFE MODE is the default.

        Real automated trading requires:

            AUTOMATION_LIVE_TRADING=true
        """

        value = getattr(
            settings,
            "AUTOMATION_LIVE_TRADING",
            False,
        )

        if isinstance(value, bool):
            return value

        return str(value).strip().lower() in {
            "true",
            "1",
            "yes",
            "on",
        }

    def start(self) -> None:
        """
        Starts the automation worker.

        The worker runs in a daemon thread so it does not
        prevent the application from shutting down.
        """

        if self.running:
            logger.info(
                "TradeFlow automation worker is already running."
            )
            return

        self.running = True

        if self.live_trading_enabled:
            logger.warning(
                "TradeFlow automation worker started "
                "with LIVE TRADING ENABLED. "
                "Real Quidax orders may be submitted."
            )
        else:
            logger.info(
                "TradeFlow automation worker started "
                "in SAFE/DRY-RUN mode. "
                "No real Quidax orders will be submitted."
            )

        import threading

        self.thread = threading.Thread(
            target=self._run,
            name="tradeflow-automation-worker",
            daemon=True,
        )

        self.thread.start()

    def stop(self) -> None:
        """
        Stops the automation worker.
        """

        self.running = False

        logger.info(
            "TradeFlow automation worker stopped."
        )

    def _run(self) -> None:
        """
        Main automation loop.

        Any error from an individual cycle is caught so
        that the background worker remains alive.
        """

        while self.running:

            try:
                self.run_once()

            except Exception:
                logger.exception(
                    "Automation cycle failed. "
                    "Worker will continue running."
                )

            import time

            time.sleep(
                self.poll_interval
            )

    def run_once(self) -> None:
        """
        Performs one automation cycle.

        Only active automation rules are evaluated.
        """

        db: Session = SessionLocal()

        try:
            rules = (
                db.query(AutomationRule)
                .filter(
                    AutomationRule.is_active.is_(True)
                )
                .all()
            )

            if not rules:
                return

            automation_service = AutomationService(
                db
            )

            trade_service = TradeService(
                db
            )

            for rule in rules:

                try:
                    self._process_rule(
                        db=db,
                        automation_service=automation_service,
                        trade_service=trade_service,
                        rule=rule,
                    )

                except Exception:
                    logger.exception(
                        "Automation rule processing failed "
                        "for %s. Continuing.",
                        rule.symbol,
                    )

        except Exception:
            db.rollback()

            logger.exception(
                "Automation worker database cycle failed."
            )

        finally:
            db.close()

    def _process_rule(
        self,
        db: Session,
        automation_service: AutomationService,
        trade_service: TradeService,
        rule: AutomationRule,
    ) -> None:
        """
        Evaluates one automation rule.
        """

        symbol = rule.symbol.upper()

        current_price = (
            self.market_data_service
            .get_price(symbol)
            .price
        )

        if current_price <= 0:
            logger.warning(
                "Ignoring invalid market price for %s: %s",
                symbol,
                current_price,
            )

            return

        # Initialize the reference price if required.
        #
        # This normally happens immediately after an
        # inactive rule is activated.
        if rule.reference_price is None:

            rule.reference_price = current_price

            db.commit()

            logger.info(
                "Automation reference initialized: "
                "%s = %s",
                symbol,
                current_price,
            )

            return

        buy_trigger_price = (
            automation_service.get_buy_trigger_price(
                rule
            )
        )

        sell_trigger_price = (
            automation_service.get_sell_trigger_price(
                rule
            )
        )

        action = (
            automation_service.get_trigger_action(
                rule=rule,
                current_price=current_price,
            )
        )

        if action is None:
            return

        logger.info(
            "Automation trigger detected: "
            "%s %s at market price %s "
            "(reference=%s, step=%s, "
            "buy_trigger=%s, sell_trigger=%s, "
            "live_trading=%s)",
            action,
            symbol,
            current_price,
            rule.reference_price,
            rule.price_step,
            buy_trigger_price,
            sell_trigger_price,
            self.live_trading_enabled,
        )

        if action == "BUY":

            self._execute_buy(
                db=db,
                trade_service=trade_service,
                rule=rule,
                current_price=current_price,
            )

            return

        if action == "SELL":

            self._execute_sell(
                db=db,
                trade_service=trade_service,
                rule=rule,
                current_price=current_price,
            )

            return

    def _execute_buy(
        self,
        db: Session,
        trade_service: TradeService,
        rule: AutomationRule,
        current_price: Decimal,
    ) -> None:
        """
        Attempts an automated BUY.

        The worker uses the currently available NGN balance.

        It does NOT calculate or hardcode a fixed trade amount.

        In SAFE/DRY-RUN mode, the dynamic balance is retrieved
        and logged but no real order is submitted.

        QuidaxExecutionProvider is responsible for normalizing
        the resulting amount to the exchange's current
        quote-currency precision.
        """

        try:
            balance_response = (
                self.quidax_account_service
                .get_balances()
            )

        except Exception:
            logger.exception(
                "Unable to retrieve Quidax balances. "
                "BUY skipped for %s.",
                rule.symbol,
            )

            return

        ngn_balance = self._get_available_balance(
            balance_response,
            "NGN",
        )

        if ngn_balance <= 0:

            logger.warning(
                "BUY skipped for %s: "
                "insufficient available NGN balance.",
                rule.symbol,
            )

            return

        buy_trigger_price = (
            rule.reference_price
            - rule.price_step
        )

        logger.info(
            "Automation BUY trigger detected for %s. "
            "Current price=%s, reference=%s, "
            "BUY trigger=%s, available NGN=%s, "
            "live_trading=%s",
            rule.symbol,
            current_price,
            rule.reference_price,
            buy_trigger_price,
            ngn_balance,
            self.live_trading_enabled,
        )

        if not self.live_trading_enabled:
            logger.warning(
                "SAFE/DRY-RUN: BUY NOT EXECUTED for %s. "
                "Would submit dynamic available NGN amount=%s "
                "to TradeService. "
                "No Quidax order was sent.",
                rule.symbol,
                ngn_balance,
            )

            return

        try:

            execution = trade_service.buy(
                symbol=rule.symbol,
                amount=ngn_balance,
            )

        except Exception:
            logger.exception(
                "Automated BUY failed for %s. "
                "Reference price will remain unchanged "
                "at %s.",
                rule.symbol,
                rule.reference_price,
            )

            return

        execution_price = Decimal(
            str(
                execution.price
            )
        )

        if execution_price <= 0:
            logger.error(
                "Automated BUY returned an invalid "
                "execution price for %s. "
                "Reference price will remain unchanged.",
                rule.symbol,
            )

            return

        previous_reference = (
            rule.reference_price
        )

        rule.reference_price = execution_price

        db.commit()

        logger.info(
            "Automated BUY completed successfully: "
            "%s quantity=%s price=%s "
            "previous_reference=%s "
            "new_reference=%s",
            rule.symbol,
            execution.quantity,
            execution_price,
            previous_reference,
            rule.reference_price,
        )

    def _execute_sell(
        self,
        db: Session,
        trade_service: TradeService,
        rule: AutomationRule,
        current_price: Decimal,
    ) -> None:
        """
        Attempts an automated SELL.

        The worker uses the currently available cryptocurrency
        balance.

        It does NOT hardcode the quantity.

        In SAFE/DRY-RUN mode, the dynamic balance is retrieved
        and logged but no real order is submitted.

        QuidaxExecutionProvider is responsible for rounding
        the quantity DOWN according to Quidax's current
        base-asset precision.
        """

        try:
            balance_response = (
                self.quidax_account_service
                .get_balances()
            )

        except Exception:
            logger.exception(
                "Unable to retrieve Quidax balances. "
                "SELL skipped for %s.",
                rule.symbol,
            )

            return

        quantity = self._get_available_balance(
            balance_response,
            rule.symbol,
        )

        if quantity <= 0:

            logger.warning(
                "SELL skipped for %s: "
                "insufficient available %s balance.",
                rule.symbol,
                rule.symbol,
            )

            return

        sell_trigger_price = (
            rule.reference_price
            + (
                rule.price_step
                * Decimal("2")
            )
        )

        logger.info(
            "Automation SELL trigger detected for %s. "
            "Current price=%s, reference=%s, "
            "SELL trigger=%s, available quantity=%s, "
            "live_trading=%s",
            rule.symbol,
            current_price,
            rule.reference_price,
            sell_trigger_price,
            quantity,
            self.live_trading_enabled,
        )

        if not self.live_trading_enabled:
            logger.warning(
                "SAFE/DRY-RUN: SELL NOT EXECUTED for %s. "
                "Would submit dynamic available quantity=%s "
                "to TradeService. "
                "No Quidax order was sent.",
                rule.symbol,
                quantity,
            )

            return

        try:

            execution = trade_service.sell(
                symbol=rule.symbol,
                quantity=quantity,
            )

        except Exception:
            logger.exception(
                "Automated SELL failed for %s. "
                "Reference price will remain unchanged "
                "at %s.",
                rule.symbol,
                rule.reference_price,
            )

            return

        execution_price = Decimal(
            str(
                execution.price
            )
        )

        if execution_price <= 0:
            logger.error(
                "Automated SELL returned an invalid "
                "execution price for %s. "
                "Reference price will remain unchanged.",
                rule.symbol,
            )

            return

        previous_reference = (
            rule.reference_price
        )

        rule.reference_price = execution_price

        db.commit()

        logger.info(
            "Automated SELL completed successfully: "
            "%s quantity=%s price=%s "
            "previous_reference=%s "
            "new_reference=%s",
            rule.symbol,
            execution.quantity,
            execution_price,
            previous_reference,
            rule.reference_price,
        )

    @staticmethod
    def _get_available_balance(
        balances,
        currency: str,
    ) -> Decimal:
        """
        Returns the available Quidax balance.

        Available balance:

            balance - locked

        Locked funds are excluded because they cannot safely
        be used for a new automated order.

        The returned value remains dynamic. No trade amount
        is hardcoded by the automation worker.
        """

        currency = currency.upper()

        for item in balances.balances:

            if item.currency.upper() != currency:
                continue

            balance = Decimal(
                str(item.balance)
            )

            locked = Decimal(
                str(item.locked)
            )

            available = (
                balance - locked
            )

            if available <= 0:
                return Decimal("0")

            return available

        return Decimal("0")