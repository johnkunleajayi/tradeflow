from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import WalletType


class WalletResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "name": "Paper Wallet",
                "wallet_type": "PAPER",
                "cash_balance": "100000.00",
                "is_active": True,
                "created_at": "2026-08-04T23:33:37Z",
                "updated_at": "2026-08-04T23:33:37Z",
            }
        },
    )

    id: int = Field(examples=[1])
    name: str = Field(examples=["Paper Wallet"])
    wallet_type: WalletType = Field(examples=["PAPER"])
    cash_balance: Decimal = Field(examples=["100000.00"])
    is_active: bool = Field(examples=[True])
    created_at: datetime = Field(examples=["2026-08-04T23:33:37Z"])
    updated_at: datetime = Field(examples=["2026-08-04T23:33:37Z"])