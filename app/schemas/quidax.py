from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class QuidaxBalanceResponse(BaseModel):
    """
    Represents a live wallet balance returned by Quidax.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "currency": "BTC",
                "balance": "0.0000403487",
                "locked": "0.0000000000",
                "staked": "0.0000000000",
            }
        }
    )

    currency: str = Field(
        examples=["BTC"]
    )

    balance: Decimal = Field(
        examples=["0.0000403487"]
    )

    locked: Decimal = Field(
        examples=["0.0000000000"]
    )

    staked: Decimal = Field(
        examples=["0.0000000000"]
    )


class QuidaxBalancesResponse(BaseModel):
    """
    Live balances for the authenticated Quidax account.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "balances": [
                    {
                        "currency": "NGN",
                        "balance": "80.2372576300",
                        "locked": "0.0000000000",
                        "staked": "0.0000000000",
                    },
                    {
                        "currency": "BTC",
                        "balance": "0.0000403487",
                        "locked": "0.0000000000",
                        "staked": "0.0000000000",
                    },
                ]
            }
        }
    )

    balances: list[QuidaxBalanceResponse]