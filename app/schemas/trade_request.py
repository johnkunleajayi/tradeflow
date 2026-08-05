from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class BuyTradeRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "symbol": "BTC",
                "amount": "10000.00",
            }
        }
    )

    symbol: str = Field(
        examples=["BTC"],
        min_length=2,
        max_length=10,
    )

    amount: Decimal = Field(
        gt=0,
        examples=["10000.00"],
    )


class SellTradeRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "symbol": "BTC",
                "quantity": "0.00005952",
            }
        }
    )

    symbol: str = Field(
        examples=["BTC"],
        min_length=2,
        max_length=10,
    )

    quantity: Decimal = Field(
        gt=0,
        examples=["0.00005952"],
    )