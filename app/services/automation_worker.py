import logging
from decimal import Decimal, ROUND_DOWN

import requests
from sqlalchemy.orm import Session

from app.core.settings import settings
from app.db.database import SessionLocal
from app.models.automation_rule import AutomationRule
from app.services.automation_service import AutomationService
from app.services.market_data_service import MarketDataService
from app.services.providers.quidax_market_provider import (
    QuidaxMarketProvider,
)
from app.services.quidax_account_service import QuidaxAccountService
from app.services.trade_service import TradeService


logger = logging.getLogger("tradeflow.automation")


class AutomationWorker:
    """
    Background worker for TradeFlow automated trading.

    Trading cycle:

        1. No open position:
               Wait for the market price to fall to the
               BUY trigger.

        2. BUY:
               Purchase the configured fixed NGN amount.

        3. Open position:
               Record the actual Quidax execution price,
               quantity, and cost.

        4. SELL:
               Wait until the current price reaches the
               calculated profitable SELL target.

        5. Close position:
               Sell only the quantity acquired by the
               current TradeFlow trading cycle.

        6. New cycle:
               Use the completed SELL price as the anchor
               for the next BUY opportunity.

    Profitability rule:

        Every automated SELL must target at least:

            AUTOMATION_MIN_PROFIT

        in net NGN profit after the configured trading fee.

    LIVE TRADING SAFETY:

        Automated BUYs use:

            AUTOMATION_TRADE_AMOUNT

        Automated SELLs use only the cryptocurrency quantity
        recorded for the current TradeFlow position.

        TradeFlow never uses the entire Quidax NGN balance
        for an automated BUY.

        TradeFlow never sells unrelated cryptocurrency
        holdings.

        In SAFE/DRY-RUN mode, no real Quidax orders are submitted.

        Real automated trading requires:

            AUTOMATION_LIVE_TRADING=true
    """

    def __init__(self):
        self.market_data_service = MarketDataService()

        self.quidax_account_service = (
            QuidaxAccountService()
        )

        self.quidax_market_provider = (
            QuidaxMarketProvider()
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

    @property
    def trade_amount(self) -> Decimal:
        """
        Returns the fixed NGN amount used for each automated BUY.
        """

        amount = Decimal(
            str(
                getattr(
                    settings,
                    "AUTOMATION_TRADE_AMOUNT",
                    "1250",
                )
            )
        )

        if amount <= 0:
            raise ValueError(
                "AUTOMATION_TRADE_AMOUNT must be greater "
                "than zero."
            )

        return amount

    def start(self) -> None:
        """
        Starts the automation worker.
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

        Any unexpected error from an individual cycle is caught
        so that the background worker remains alive.
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

        The worker evaluates only one side of the trading
        cycle at a time:

            No position:
                BUY logic.

            Open position:
                SELL logic.

        A temporary Quidax market-data/network failure is treated
        as a skipped cycle rather than a trading-rule failure.
        """

        symbol = rule.symbol.upper()

        try:
            current_price = (
                self.market_data_service
                .get_price(symbol)
                .price
            )

        except requests.RequestException as exc:
            logger.warning(
                "Unable to retrieve current market price "
                "for %s from Quidax. "
                "Skipping this automation cycle. "
                "The worker will retry automatically. "
                "Reason: %s",
                symbol,
                exc,
            )
            return

        except Exception as exc:
            logger.warning(
                "Unable to retrieve current market price "
                "for %s. "
                "Skipping this automation cycle. "
                "The worker will retry automatically. "
                "Reason: %s",
                symbol,
                exc,
            )
            return

        if current_price <= 0:
            logger.warning(
                "Ignoring invalid market price for %s: %s",
                symbol,
                current_price,
            )

            return

        if (
            not rule.position_open
            and rule.reference_price is None
        ):
            rule.reference_price = current_price

            db.commit()

            logger.info(
                "Automation BUY reference initialized: "
                "%s = %s",
                symbol,
                current_price,
            )

            return

        action = (
            automation_service.get_trigger_action(
                rule=rule,
                current_price=current_price,
            )
        )

        if action is None:
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

        logger.info(
            "Automation trigger detected: "
            "%s %s at market price %s "
            "(reference=%s, step=%s, "
            "buy_trigger=%s, sell_target=%s, "
            "position_open=%s, trade_amount=%s, "
            "live_trading=%s)",
            action,
            symbol,
            current_price,
            rule.reference_price,
            rule.price_step,
            buy_trigger_price,
            sell_trigger_price,
            rule.position_open,
            self.trade_amount,
            self.live_trading_enabled,
        )

        if action == "BUY":

            self._execute_buy(
                db=db,
                automation_service=automation_service,
                trade_service=trade_service,
                rule=rule,
                current_price=current_price,
            )

            return

        if action == "SELL":

            self._execute_sell(
                db=db,
                automation_service=automation_service,
                trade_service=trade_service,
                rule=rule,
                current_price=current_price,
            )

            return

    def _execute_buy(
        self,
        db: Session,
        automation_service: AutomationService,
        trade_service: TradeService,
        rule: AutomationRule,
        current_price: Decimal,
    ) -> None:
        """
        Executes an automated BUY.

        BUYs are allowed only when no position is currently open.

        The configured fixed NGN amount is used.

        After successful execution, the actual Quidax
        execution details are persisted as the open position.
        """

        if rule.position_open:

            logger.warning(
                "BUY skipped for %s: "
                "an automated position is already open.",
                rule.symbol,
            )

            return

        try:
            balance_response = (
                self.quidax_account_service
                .get_balances()
            )

        except requests.RequestException as exc:
            logger.warning(
                "Unable to retrieve Quidax balances "
                "for BUY of %s. "
                "BUY skipped; worker will retry automatically. "
                "Reason: %s",
                rule.symbol,
                exc,
            )

            return

        except Exception as exc:
            logger.warning(
                "Unable to retrieve Quidax balances "
                "for BUY of %s. "
                "BUY skipped; worker will retry automatically. "
                "Reason: %s",
                rule.symbol,
                exc,
            )

            return

        ngn_balance = self._get_available_balance(
            balance_response,
            "NGN",
        )

        trade_amount = self.trade_amount

        if ngn_balance < trade_amount:

            logger.warning(
                "BUY skipped for %s: "
                "available NGN=%s is below the "
                "configured automation trade amount=%s.",
                rule.symbol,
                ngn_balance,
                trade_amount,
            )

            return

        buy_trigger_price = (
            rule.reference_price
            - rule.price_step
        )

        logger.info(
            "Automation BUY opportunity for %s. "
            "Current price=%s, reference=%s, "
            "BUY trigger=%s, available NGN=%s, "
            "trade amount=%s, live_trading=%s",
            rule.symbol,
            current_price,
            rule.reference_price,
            buy_trigger_price,
            ngn_balance,
            trade_amount,
            self.live_trading_enabled,
        )

        if not self.live_trading_enabled:
            logger.warning(
                "SAFE/DRY-RUN: BUY NOT EXECUTED for %s. "
                "Would submit fixed NGN amount=%s. "
                "No Quidax order was sent.",
                rule.symbol,
                trade_amount,
            )

            return

        try:

            execution = trade_service.buy(
                symbol=rule.symbol,
                amount=trade_amount,
            )

        except requests.RequestException as exc:
            logger.warning(
                "Automated BUY request failed for %s. "
                "No position state was changed. "
                "Worker will retry on a future trigger cycle. "
                "Reason: %s",
                rule.symbol,
                exc,
            )

            return

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

        execution_quantity = Decimal(
            str(
                execution.quantity
            )
        )

        execution_cost = Decimal(
            str(
                execution.amount
            )
        )

        if execution_price <= 0:
            logger.error(
                "Automated BUY returned an invalid "
                "execution price for %s. "
                "Position will not be opened.",
                rule.symbol,
            )

            return

        if execution_quantity <= 0:
            logger.error(
                "Automated BUY returned an invalid "
                "execution quantity for %s. "
                "Position will not be opened.",
                rule.symbol,
            )

            return

        if execution_cost <= 0:
            logger.error(
                "Automated BUY returned an invalid "
                "execution cost for %s. "
                "Position will not be opened.",
                rule.symbol,
            )

            return

        try:

            automation_service.set_position(
                rule=rule,
                entry_price=execution_price,
                entry_quantity=execution_quantity,
                entry_cost=execution_cost,
            )

        except Exception:
            db.rollback()

            logger.exception(
                "Automated BUY completed on Quidax, "
                "but TradeFlow could not persist the "
                "position state for %s.",
                rule.symbol,
            )

            return

        logger.info(
            "Automated BUY completed successfully: "
            "%s quantity=%s entry_price=%s "
            "entry_cost=%s target_sell_price=%s",
            rule.symbol,
            execution_quantity,
            execution_price,
            execution_cost,
            rule.target_sell_price,
        )

    def _execute_sell(
        self,
        db: Session,
        automation_service: AutomationService,
        trade_service: TradeService,
        rule: AutomationRule,
        current_price: Decimal,
    ) -> None:
        """
        Executes an automated SELL.

        Only the quantity recorded for the current TradeFlow
        position may be sold.

        The worker verifies that the actual Quidax balance
        still contains enough of the asset.

        The SELL is allowed only when the current price has
        reached the profitable target.
        """

        if not rule.position_open:

            logger.warning(
                "SELL skipped for %s: "
                "no TradeFlow position is open.",
                rule.symbol,
            )

            return

        if (
            rule.entry_quantity is None
            or rule.entry_quantity <= 0
        ):

            logger.error(
                "SELL skipped for %s: "
                "open position has no valid entry quantity.",
                rule.symbol,
            )

            return

        if (
            rule.entry_cost is None
            or rule.entry_cost <= 0
        ):

            logger.error(
                "SELL skipped for %s: "
                "open position has no valid entry cost.",
                rule.symbol,
            )

            return

        target_sell_price = (
            automation_service.get_sell_trigger_price(
                rule
            )
        )

        if target_sell_price is None:

            logger.error(
                "SELL skipped for %s: "
                "no valid target SELL price exists.",
                rule.symbol,
            )

            return

        if current_price < target_sell_price:

            return

        try:
            balance_response = (
                self.quidax_account_service
                .get_balances()
            )

        except requests.RequestException as exc:
            logger.warning(
                "Unable to retrieve Quidax balances "
                "for SELL of %s. "
                "SELL skipped; worker will retry automatically. "
                "Reason: %s",
                rule.symbol,
                exc,
            )

            return

        except Exception as exc:
            logger.warning(
                "Unable to retrieve Quidax balances "
                "for SELL of %s. "
                "SELL skipped; worker will retry automatically. "
                "Reason: %s",
                rule.symbol,
                exc,
            )

            return

        available_balance = (
            self._get_available_balance(
                balance_response,
                rule.symbol,
            )
        )

        sell_quantity = min(
            rule.entry_quantity,
            available_balance,
        )

        if sell_quantity <= 0:

            logger.warning(
                "SELL skipped for %s: "
                "no available Quidax %s balance.",
                rule.symbol,
                rule.symbol,
            )

            return

        try:
            rules = (
                self.quidax_market_provider
                .get_market_rules(
                    rule.symbol
                )
            )

            base_precision = self._get_precision(
                rules,
                "base_precision",
                8,
            )

            minimum_order_size = (
                self._get_minimum_order_size(
                    rules
                )
            )

            normalized_quantity = (
                self._quantize_down(
                    sell_quantity,
                    base_precision
                )
            )

        except requests.RequestException as exc:
            logger.warning(
                "Unable to retrieve Quidax market rules "
                "for SELL of %s. "
                "SELL skipped; worker will retry automatically. "
                "Reason: %s",
                rule.symbol,
                exc,
            )

            return

        except Exception:
            logger.exception(
                "Unable to validate Quidax SELL rules "
                "for %s. SELL skipped.",
                rule.symbol,
            )

            return

        if normalized_quantity <= 0:

            logger.info(
                "SELL skipped for %s: position quantity=%s "
                "becomes zero after Quidax base precision "
                "normalization to %s decimal places.",
                rule.symbol,
                sell_quantity,
                base_precision,
            )

            return

        estimated_quote_value = (
            normalized_quantity
            * current_price
        )

        if (
            minimum_order_size > 0
            and estimated_quote_value
            < minimum_order_size
        ):

            logger.info(
                "SELL skipped for %s: normalized position "
                "quantity=%s has estimated value=%s NGN, "
                "below Quidax minimum order value=%s NGN.",
                rule.symbol,
                normalized_quantity,
                estimated_quote_value,
                minimum_order_size,
            )

            return

        logger.info(
            "Automation profitable SELL opportunity for %s. "
            "Current price=%s, target=%s, "
            "entry_price=%s, entry_cost=%s, "
            "position_quantity=%s, sell_quantity=%s, "
            "live_trading=%s",
            rule.symbol,
            current_price,
            target_sell_price,
            rule.entry_price,
            rule.entry_cost,
            rule.entry_quantity,
            normalized_quantity,
            self.live_trading_enabled,
        )

        if not self.live_trading_enabled:
            logger.warning(
                "SAFE/DRY-RUN: SELL NOT EXECUTED for %s. "
                "Would sell quantity=%s at market price "
                "around %s. No Quidax order was sent.",
                rule.symbol,
                normalized_quantity,
                current_price,
            )

            return

        try:

            execution = trade_service.sell(
                symbol=rule.symbol,
                quantity=normalized_quantity,
            )

        except requests.RequestException as exc:
            logger.warning(
                "Automated SELL request failed for %s. "
                "Position remains open. "
                "Worker will retry when the target condition "
                "is still satisfied. "
                "Reason: %s",
                rule.symbol,
                exc,
            )

            return

        except Exception:
            logger.exception(
                "Automated SELL failed for %s. "
                "Position remains open and target "
                "price remains %s.",
                rule.symbol,
                target_sell_price,
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
                "Position remains open.",
                rule.symbol,
            )

            return

        previous_entry_cost = (
            rule.entry_cost
        )

        actual_net_amount = Decimal(
            str(
                execution.amount
            )
        )

        actual_profit = (
            actual_net_amount
            - previous_entry_cost
        )

        minimum_profit = (
            automation_service.minimum_profit
        )

        if actual_profit < minimum_profit:

            logger.error(
                "Automated SELL completed for %s, but "
                "reported net profit=%s is below the "
                "required minimum profit=%s. "
                "The position will be closed because "
                "the exchange execution has already completed.",
                rule.symbol,
                actual_profit,
                minimum_profit,
            )

        previous_reference = (
            rule.reference_price
        )

        automation_service.close_position(
            rule=rule,
            reference_price=execution_price,
        )

        logger.info(
            "Automated SELL completed successfully: "
            "%s quantity=%s price=%s "
            "net_amount=%s previous_entry_cost=%s "
            "actual_net_profit=%s "
            "previous_reference=%s "
            "new_reference=%s",
            rule.symbol,
            execution.quantity,
            execution_price,
            actual_net_amount,
            previous_entry_cost,
            actual_profit,
            previous_reference,
            rule.reference_price,
        )

    @staticmethod
    def _quantize_down(
        value: Decimal,
        precision: int,
    ) -> Decimal:
        """
        Rounds a quantity DOWN to the specified number of
        decimal places.
        """

        quantum = Decimal("1").scaleb(
            -precision
        )

        return value.quantize(
            quantum,
            rounding=ROUND_DOWN,
        )

    @staticmethod
    def _get_precision(
        rules: dict,
        key: str,
        default: int,
    ) -> int:
        """
        Safely extracts a precision value from Quidax rules.
        """

        value = rules.get(
            key,
            default,
        )

        try:
            precision = int(value)
        except (
            TypeError,
            ValueError,
        ) as exc:
            raise ValueError(
                f"Invalid Quidax {key}: {value!r}"
            ) from exc

        if precision < 0:
            raise ValueError(
                f"Invalid Quidax {key}: {precision}"
            )

        return precision

    @staticmethod
    def _get_minimum_order_size(
        rules: dict,
    ) -> Decimal:
        """
        Extracts Quidax's minimum order size.
        """

        value = rules.get(
            "minimum_order_size",
            "0",
        )

        try:
            minimum = Decimal(
                str(value)
            )
        except Exception as exc:
            raise ValueError(
                "Invalid Quidax minimum_order_size: "
                f"{value!r}"
            ) from exc

        if minimum < 0:
            raise ValueError(
                "Quidax minimum order size cannot be negative."
            )

        return minimum

    @staticmethod
    def _get_available_balance(
        balances,
        currency: str,
    ) -> Decimal:
        """
        Returns the available Quidax balance.

        Available balance:

            balance - locked
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