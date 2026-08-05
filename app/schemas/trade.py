from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class TradeResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "wallet_id": 1,
                "symbol": "BTC",
                "side": "BUY",
                "quantity": "0.00250000",
                "price": "168000000.00",
                "total_value": "420000.00",
                "created_at": "2026-08-05T00:00:00Z",
            }
        },
    )

    id: int = Field(examples=[1])
    wallet_id: int = Field(examples=[1])
    symbol: str = Field(examples=["BTC"])
    side: str = Field(examples=["BUY"])
    quantity: Decimal = Field(examples=["0.00250000"])
    price: Decimal = Field(examples=["168000000.00"])
    total_value: Decimal = Field(examples=["420000.00"])
    created_at: datetime = Field(examples=["2026-08-05T00:00:00Z"])


class BuyTradeResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "symbol": "BTC",
                "amount": "10000.00",
                "price": "168000000.00",
                "quantity": "0.00005952",
            }
        }
    )

    symbol: str = Field(examples=["BTC"])
    amount: Decimal = Field(examples=["10000.00"])
    price: Decimal = Field(examples=["168000000.00"])
    quantity: Decimal = Field(examples=["0.00005952"])


class SellTradeResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "symbol": "BTC",
                "amount": "10000.00",
                "price": "168000000.00",
                "quantity": "0.00005952",
            }
        }
    )

    symbol: str = Field(examples=["BTC"])
    amount: Decimal = Field(examples=["10000.00"])
    price: Decimal = Field(examples=["168000000.00"])
    quantity: Decimal = Field(examples=["0.00005952"])