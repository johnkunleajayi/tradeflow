from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.automation_rule import AutomationRule
from app.services.market_data_service import MarketDataService


class AutomationService:
    """
    Handles TradeFlow's basic automated trading rules.

    MVP behaviour:

        BUY:
            Current BTC price falls by price_step
            from the automation reference price.

        SELL:
            Current BTC price rises by price_step
            from the automation reference price.

    This service only handles the automation rule itself.

    Actual BUY/SELL execution remains the responsibility
    of TradeService.
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

        Only one active rule per symbol is needed
        for the MVP.
        """

        symbol = symbol.upper()

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
        Activates an existing automation rule.
        """

        rule = self.get_rule(symbol)

        if rule is None:
            raise ValueError(
                f"No automation rule exists for "
                f"{symbol.upper()}."
            )

        rule.is_active = True

        self.db.commit()
        self.db.refresh(rule)

        return rule

    def deactivate(
        self,
        symbol: str,
    ) -> AutomationRule:
        """
        Stops an existing automation rule.
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

    def get_status(
        self,
        symbol: str,
    ) -> dict:
        """
        Returns the current automation information.

        The actual reference price will be introduced
        when the automation worker is added.
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

        return {
            "id": rule.id,
            "symbol": rule.symbol,
            "price_step": rule.price_step,
            "is_active": rule.is_active,
            "reference_price": None,
            "current_price": current_price,
            "next_buy_price": None,
            "next_sell_price": None,
        }