from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class HoldingResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "wallet_id": 1,
                "symbol": "BTC",
                "quantity": "0.00250000",
                "average_buy_price": "168000000.00",
                "created_at": "2026-08-05T00:00:00Z",
                "updated_at": "2026-08-05T00:00:00Z",
            }
        },
    )

    id: int = Field(examples=[1])
    wallet_id: int = Field(examples=[1])
    symbol: str = Field(examples=["BTC"])
    quantity: Decimal = Field(examples=["0.00250000"])
    average_buy_price: Decimal = Field(examples=["168000000.00"])
    created_at: datetime = Field(examples=["2026-08-05T00:00:00Z"])
    updated_at: datetime = Field(examples=["2026-08-05T00:00:00Z"])