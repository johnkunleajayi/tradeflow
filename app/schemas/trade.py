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
                "quantity": "0.00005946048000",
                "price": "168000000.00",
                "total_value": "10000.00000000",
                "fee": "0.00000005952000",
                "fee_currency": "BTC",
                "net_value": "10000.00000000",
                "created_at": "2026-08-05T00:00:00Z",
            }
        },
    )

    id: int = Field(examples=[1])

    wallet_id: int = Field(
        examples=[1],
    )

    symbol: str = Field(
        examples=["BTC"],
    )

    side: str = Field(
        examples=["BUY"],
    )

    quantity: Decimal = Field(
        examples=["0.00005946048000"],
    )

    price: Decimal = Field(
        examples=["168000000.00"],
    )

    total_value: Decimal = Field(
        examples=["10000.00000000"],
    )

    fee: Decimal = Field(
        examples=["0.00000005952000"],
    )

    fee_currency: str = Field(
        examples=["BTC"],
    )

    net_value: Decimal = Field(
        examples=["10000.00000000"],
    )

    created_at: datetime = Field(
        examples=["2026-08-05T00:00:00Z"],
    )


class BuyTradeResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "symbol": "BTC",
                "amount": "10000.00000000",
                "price": "168000000.00",
                "quantity": "0.00005994048000",
                "gross_quantity": "0.00006000000000",
                "fee": "0.00000006000000",
                "fee_currency": "BTC",
                "net_value": "10000.00000000",
            }
        }
    )

    symbol: str = Field(
        examples=["BTC"],
    )

    # Actual quote currency spent.
    amount: Decimal = Field(
        examples=["10000.00000000"],
    )

    price: Decimal = Field(
        examples=["168000000.00"],
    )

    # Net cryptocurrency received.
    quantity: Decimal = Field(
        examples=["0.00005994048000"],
    )

    # Cryptocurrency quantity before the base-asset fee.
    gross_quantity: Decimal = Field(
        examples=["0.00006000000000"],
    )

    fee: Decimal = Field(
        examples=["0.00000006000000"],
    )

    fee_currency: str = Field(
        examples=["BTC"],
    )

    net_value: Decimal = Field(
        examples=["10000.00000000"],
    )


class SellTradeResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "symbol": "BTC",
                "amount": "9989.99000000",
                "gross_amount": "10000.00000000",
                "price": "168000000.00",
                "quantity": "0.00005952",
                "fee": "10.00000000",
                "fee_currency": "NGN",
                "net_value": "9989.99000000",
            }
        }
    )

    symbol: str = Field(
        examples=["BTC"],
    )

    # Net NGN proceeds after fee.
    amount: Decimal = Field(
        examples=["9989.99000000"],
    )

    # Gross NGN proceeds before fee.
    gross_amount: Decimal = Field(
        examples=["10000.00000000"],
    )

    price: Decimal = Field(
        examples=["168000000.00"],
    )

    # Actual BTC sold.
    quantity: Decimal = Field(
        examples=["0.00005952"],
    )

    fee: Decimal = Field(
        examples=["10.00000000"],
    )

    fee_currency: str = Field(
        examples=["NGN"],
    )

    net_value: Decimal = Field(
        examples=["9989.99000000"],
    )