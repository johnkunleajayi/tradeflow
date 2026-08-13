from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.automation_rule import AutomationRule
from app.services.market_data_service import MarketDataService


class AutomationService:
    """
    Handles TradeFlow's automated trading rules.

    MVP strategy:

        BUY:
            Current price <= reference price - price_step

        SELL:
            Current price >= reference price + (price_step * 2)

    The actual trade is executed by TradeService.

    The reference price is persisted in the database so
    automation can safely survive application restarts.
    """

    def __init__(
        self,
        db: Session,
    ):
        self.db = db
        self.market_data_service = MarketDataService()

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

        If no reference price exists, the current market
        price becomes the initial reference price.

        Existing reference prices are preserved.
        """

        rule = self.get_rule(symbol)

        if rule is None:
            raise ValueError(
                f"No automation rule exists for "
                f"{symbol.upper()}."
            )

        if rule.reference_price is None:
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

        The reference price is deliberately preserved so
        restarting automation does not unexpectedly reset
        the strategy.
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

        The reference price is cleared so that the next
        activation obtains a fresh reference price from
        the current market price.

        The configured price_step is preserved.
        """

        rule = self.get_rule(symbol)

        if rule is None:
            raise ValueError(
                f"No automation rule exists for "
                f"{symbol.upper()}."
            )

        rule.reference_price = None
        rule.is_active = False

        self.db.commit()
        self.db.refresh(rule)

        return rule

    def set_reference_price(
        self,
        rule: AutomationRule,
        price: Decimal,
    ) -> AutomationRule:
        """
        Updates the persisted automation reference price.
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

        Strategy:

            BUY = reference price - price_step

        If no reference price exists, there is no valid
        BUY trigger.
        """

        if rule.reference_price is None:
            return None

        return (
            rule.reference_price
            - rule.price_step
        )

    def get_sell_trigger_price(
        self,
        rule: AutomationRule,
    ) -> Decimal | None:
        """
        Returns the next SELL trigger price.

        Strategy:

            SELL = reference price + (price_step * 2)

        If no reference price exists, there is no valid
        SELL trigger.
        """

        if rule.reference_price is None:
            return None

        return (
            rule.reference_price
            + (
                rule.price_step
                * Decimal("2")
            )
        )

    def get_trigger_action(
        self,
        rule: AutomationRule,
        current_price: Decimal,
    ) -> str | None:
        """
        Determines whether the current price has triggered
        a BUY or SELL.

        Strategy:

            BUY:
                reference - price_step

            SELL:
                reference + (price_step * 2)

        Returns:

            BUY
            SELL
            None
        """

        if not rule.is_active:
            return None

        if rule.reference_price is None:
            return None

        if current_price <= 0:
            return None

        buy_trigger = (
            self.get_buy_trigger_price(rule)
        )

        sell_trigger = (
            self.get_sell_trigger_price(rule)
        )

        if buy_trigger is not None:
            if current_price <= buy_trigger:
                return "BUY"

        if sell_trigger is not None:
            if current_price >= sell_trigger:
                return "SELL"

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
        }