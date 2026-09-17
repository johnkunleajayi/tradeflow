from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.settings import settings
from app.models.automation_rule import AutomationRule
from app.services.market_data_service import MarketDataService
from app.services.trade_service import TradeService


class AutomationService:
    """
    Handles TradeFlow's automated trading rules.

    MVP strategy:

        BUY:
            When there is NO open position and the current
            market price falls to or below:

                reference_price - price_step

        SELL:
            When there IS an open position and the current
            market price reaches the calculated target_sell_price.

    The SELL target is calculated from the actual BUY execution.

    The minimum required profit is:

        AUTOMATION_MIN_PROFIT

    The configured trading fee rate is included when calculating
    the minimum profitable SELL price.

    The actual exchange execution is handled by TradeService.

    The automation rule persists the current trading-cycle state
    so automation can safely survive application restarts.
    """

    def __init__(
        self,
        db: Session,
    ):
        self.db = db
        self.market_data_service = MarketDataService()
        self.trade_service = TradeService(db)

    @property
    def fee_rate(self) -> Decimal:
        """
        Returns the configured trading fee rate.
        """

        return Decimal(
            str(
                settings.QUIDAX_TRADING_FEE_RATE
            )
        )

    @property
    def minimum_profit(self) -> Decimal:
        """
        Returns the minimum required net profit for an
        automated trading cycle.
        """

        profit = Decimal(
            str(
                getattr(
                    settings,
                    "AUTOMATION_MIN_PROFIT",
                    "75",
                )
            )
        )

        if profit <= 0:
            raise ValueError(
                "AUTOMATION_MIN_PROFIT must be greater "
                "than zero."
            )

        return profit

    def get_rule(
        self,
        symbol: str,
    ) -> AutomationRule | None:
        """
        Returns the automation rule for a symbol.
        """

        return (
            self.db.query(AutomationRule)
            .filter(
                AutomationRule.symbol
                == symbol.upper()
            )
            .first()
        )

    def create_rule(
        self,
        symbol: str,
        price_step: Decimal,
    ) -> AutomationRule:
        """
        Creates an automation rule.
        """

        symbol = symbol.upper().strip()

        if not symbol:
            raise ValueError(
                "Trading symbol is required."
            )

        if price_step <= 0:
            raise ValueError(
                "Price step must be greater than zero."
            )

        existing_rule = self.get_rule(
            symbol
        )

        if existing_rule is not None:
            raise ValueError(
                f"An automation rule already exists for "
                f"{symbol}."
            )

        rule = AutomationRule(
            symbol=symbol,
            price_step=price_step,
            reference_price=None,
            position_open=False,
            entry_price=None,
            entry_quantity=None,
            entry_cost=None,
            target_sell_price=None,
            is_active=False,
        )

        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)

        return rule

    def activate(
        self,
        symbol: str,
    ) -> AutomationRule:
        """
        Activates automation.

        If no reference price exists and there is no open
        position, the current market price becomes the initial
        BUY reference.

        Existing reference prices and open positions are
        preserved.
        """

        rule = self.get_rule(symbol)

        if rule is None:
            raise ValueError(
                f"No automation rule exists for "
                f"{symbol.upper()}."
            )

        if (
            rule.reference_price is None
            and not rule.position_open
        ):
            current_price = (
                self.market_data_service
                .get_price(rule.symbol)
                .price
            )

            if current_price <= 0:
                raise ValueError(
                    "Current market price must be greater "
                    "than zero."
                )

            rule.reference_price = current_price

        rule.is_active = True

        self.db.commit()
        self.db.refresh(rule)

        return rule

    def deactivate(
        self,
        symbol: str,
    ) -> AutomationRule:
        """
        Stops automation.

        The current reference price and any open position
        are deliberately preserved so restarting automation
        does not unexpectedly reset the trading cycle.
        """

        rule = self.get_rule(symbol)

        if rule is None:
            raise ValueError(
                f"No automation rule exists for "
                f"{symbol.upper()}."
            )

        rule.is_active = False

        self.db.commit()
        self.db.refresh(rule)

        return rule

    def reset(
        self,
        symbol: str,
    ) -> AutomationRule:
        """
        Resets automation to a clean inactive state.

        A reset is not allowed while a position is open because
        clearing the local position state while the corresponding
        cryptocurrency remains on the live exchange could cause
        TradeFlow to lose track of an actual live position.

        The configured price_step is preserved.
        """

        rule = self.get_rule(symbol)

        if rule is None:
            raise ValueError(
                f"No automation rule exists for "
                f"{symbol.upper()}."
            )

        if rule.position_open:
            raise ValueError(
                "Cannot reset automation while a position "
                "is open. Close the position first."
            )

        rule.reference_price = None
        rule.position_open = False
        rule.entry_price = None
        rule.entry_quantity = None
        rule.entry_cost = None
        rule.target_sell_price = None
        rule.is_active = False

        self.db.commit()
        self.db.refresh(rule)

        return rule

    def delete_rule(
        self,
        symbol: str,
    ) -> None:
        """
        Permanently deletes the automation rule for a symbol.
        """

        rule = self.get_rule(symbol)

        if rule is None:
            raise ValueError(
                f"No automation rule exists for "
                f"{symbol.upper()}."
            )

        if rule.position_open:
            raise ValueError(
                "Cannot delete an automation rule while "
                "a position is open."
            )

        self.db.delete(rule)
        self.db.commit()

    def set_reference_price(
        self,
        rule: AutomationRule,
        price: Decimal,
    ) -> AutomationRule:
        """
        Updates the persisted BUY reference price.

        Reference price is only used when TradeFlow does not
        currently have an open position.
        """

        if price <= 0:
            raise ValueError(
                "Reference price must be greater than zero."
            )

        rule.reference_price = price

        self.db.commit()
        self.db.refresh(rule)

        return rule

    def get_buy_trigger_price(
        self,
        rule: AutomationRule,
    ) -> Decimal | None:
        """
        Returns the next BUY trigger price.

        BUY is only available when there is no open position.

            BUY = reference price - price_step
        """

        if rule.reference_price is None:
            return None

        if rule.position_open:
            return None

        return (
            rule.reference_price
            - rule.price_step
        )

    def calculate_target_sell_price(
        self,
        rule: AutomationRule,
    ) -> Decimal:
        """
        Calculates the minimum SELL price required to achieve
        the configured net profit after the estimated SELL fee.

        Required net proceeds:

            entry_cost + minimum_profit

        SELL net proceeds:

            quantity * sell_price * (1 - fee_rate)

        Therefore:

            target_sell_price =
                (entry_cost + minimum_profit)
                /
                (quantity * (1 - fee_rate))
        """

        if not rule.position_open:
            raise ValueError(
                "Cannot calculate a SELL target without "
                "an open position."
            )

        if (
            rule.entry_quantity is None
            or rule.entry_quantity <= 0
        ):
            raise ValueError(
                "Open position has no valid entry quantity."
            )

        if (
            rule.entry_cost is None
            or rule.entry_cost <= 0
        ):
            raise ValueError(
                "Open position has no valid entry cost."
            )

        fee_rate = self.fee_rate

        if fee_rate < 0:
            raise ValueError(
                "Trading fee rate cannot be negative."
            )

        if fee_rate >= 1:
            raise ValueError(
                "Trading fee rate must be less than 1."
            )

        fee_multiplier = (
            Decimal("1")
            - fee_rate
        )

        required_proceeds = (
            rule.entry_cost
            + self.minimum_profit
        )

        target_price = (
            required_proceeds
            / (
                rule.entry_quantity
                * fee_multiplier
            )
        )

        if target_price <= 0:
            raise ValueError(
                "Calculated SELL target price must be "
                "greater than zero."
            )

        return target_price

    def get_sell_trigger_price(
        self,
        rule: AutomationRule,
    ) -> Decimal | None:
        """
        Returns the profitable SELL target for the current
        open position.

        No SELL trigger exists when there is no open position.
        """

        if not rule.position_open:
            return None

        if rule.target_sell_price is not None:
            return rule.target_sell_price

        return self.calculate_target_sell_price(
            rule
        )

    def set_position(
        self,
        rule: AutomationRule,
        entry_price: Decimal,
        entry_quantity: Decimal,
        entry_cost: Decimal,
    ) -> AutomationRule:
        """
        Opens a new automated trading position using the
        actual completed BUY execution.

        The profitable SELL target is calculated immediately.
        """

        if entry_price <= 0:
            raise ValueError(
                "Entry price must be greater than zero."
            )

        if entry_quantity <= 0:
            raise ValueError(
                "Entry quantity must be greater than zero."
            )

        if entry_cost <= 0:
            raise ValueError(
                "Entry cost must be greater than zero."
            )

        rule.position_open = True
        rule.entry_price = entry_price
        rule.entry_quantity = entry_quantity
        rule.entry_cost = entry_cost

        rule.target_sell_price = (
            self.calculate_target_sell_price(
                rule
            )
        )

        self.db.commit()
        self.db.refresh(rule)

        return rule

    def close_position(
        self,
        rule: AutomationRule,
        reference_price: Decimal | None = None,
    ) -> AutomationRule:
        """
        Closes the current automated trading position.

        All position-specific state is cleared.

        If a reference price is supplied, it becomes the anchor
        for the next BUY cycle.
        """

        if reference_price is not None:

            if reference_price <= 0:
                raise ValueError(
                    "Reference price must be greater "
                    "than zero."
                )

            rule.reference_price = reference_price

        rule.position_open = False
        rule.entry_price = None
        rule.entry_quantity = None
        rule.entry_cost = None
        rule.target_sell_price = None

        self.db.commit()
        self.db.refresh(rule)

        return rule

    def close_position_manually(
        self,
        symbol: str,
    ):
        """
        Manually closes the currently tracked position.

        The SELL is executed through TradeService first.

        The automation position is cleared only after the
        exchange execution succeeds.

        The actual executed SELL price becomes the reference
        price for the next BUY cycle.
        """

        rule = self.get_rule(symbol)

        if rule is None:
            raise ValueError(
                f"No automation rule exists for "
                f"{symbol.upper()}."
            )

        if not rule.position_open:
            raise ValueError(
                f"No open automation position exists "
                f"for {rule.symbol}."
            )

        if (
            rule.entry_quantity is None
            or rule.entry_quantity <= 0
        ):
            raise ValueError(
                "Open position has no valid entry quantity."
            )

        sell_response = self.trade_service.sell(
            symbol=rule.symbol,
            quantity=rule.entry_quantity,
        )

        if sell_response is None:
            raise RuntimeError(
                f"Manual SELL returned no result for "
                f"{rule.symbol}."
            )

        executed_price = Decimal(
            str(
                sell_response.price
            )
        )

        executed_quantity = Decimal(
            str(
                sell_response.quantity
            )
        )

        if executed_price <= 0:
            raise RuntimeError(
                "Manual SELL returned an invalid "
                "execution price."
            )

        if executed_quantity <= 0:
            raise RuntimeError(
                "Manual SELL returned an invalid "
                "execution quantity."
            )

        self.close_position(
            rule=rule,
            reference_price=executed_price,
        )

        return sell_response

    def get_trigger_action(
        self,
        rule: AutomationRule,
        current_price: Decimal,
    ) -> str | None:
        """
        Determines whether the current price has triggered
        a BUY or profitable SELL.

        BUY:
            Only when there is no open position.

        SELL:
            Only when there is an open position and the
            current price reaches the calculated target price.
        """

        if not rule.is_active:
            return None

        if current_price <= 0:
            return None

        if rule.position_open:

            sell_trigger = (
                self.get_sell_trigger_price(
                    rule
                )
            )

            if (
                sell_trigger is not None
                and current_price >= sell_trigger
            ):
                return "SELL"

            return None

        buy_trigger = (
            self.get_buy_trigger_price(
                rule
            )
        )

        if (
            buy_trigger is not None
            and current_price <= buy_trigger
        ):
            return "BUY"

        return None

    def get_status(
        self,
        symbol: str,
    ) -> dict:
        """
        Returns the current automation information.
        """

        symbol = symbol.upper()

        rule = self.get_rule(symbol)

        if rule is None:
            raise ValueError(
                f"No automation rule exists for {symbol}."
            )

        current_price = (
            self.market_data_service
            .get_price(symbol)
            .price
        )

        next_buy_price = (
            self.get_buy_trigger_price(rule)
        )

        next_sell_price = (
            self.get_sell_trigger_price(rule)
        )

        return {
            "id": rule.id,
            "symbol": rule.symbol,
            "price_step": rule.price_step,
            "is_active": rule.is_active,
            "reference_price": rule.reference_price,
            "current_price": current_price,
            "next_buy_price": next_buy_price,
            "next_sell_price": next_sell_price,
            "position_open": rule.position_open,
            "entry_price": rule.entry_price,
            "entry_quantity": rule.entry_quantity,
            "entry_cost": rule.entry_cost,
            "target_sell_price": rule.target_sell_price,
            "minimum_profit": self.minimum_profit,
        }