from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class AutomationRuleCreateRequest(BaseModel):
    symbol: str = Field(
        default="BTC",
        examples=["BTC"],
    )

    price_step: Decimal = Field(
        examples=["100000"],
    )


class AutomationRuleResponse(BaseModel):
    id: int

    symbol: str

    price_step: Decimal

    is_active: bool

    created_at: datetime

    updated_at: datetime


class AutomationStatusResponse(BaseModel):
    id: int

    symbol: str

    price_step: Decimal

    is_active: bool

    reference_price: Decimal | None = None

    current_price: Decimal | None = None

    next_buy_price: Decimal | None = None

    next_sell_price: Decimal | None = None