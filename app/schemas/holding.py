from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class HoldingResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "symbol": "BTC",
                "quantity": "0.00250000",
            }
        },
    )

    symbol: str = Field(
        examples=["BTC"]
    )

    quantity: Decimal = Field(
        examples=["0.00250000"]
    )