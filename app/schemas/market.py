from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class MarketPriceResponse(BaseModel):
    """
    Represents the current market price of a single asset.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "symbol": "BTC",
                "price": "168000000.00",
            }
        }
    )

    symbol: str = Field(
        examples=["BTC"],
    )

    price: Decimal = Field(
        examples=["168000000.00"],
    )


class MarketPricesResponse(BaseModel):
    """
    Represents all supported market prices.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "prices": [
                    {
                        "symbol": "BTC",
                        "price": "168000000.00",
                    },
                    {
                        "symbol": "ETH",
                        "price": "5200000.00",
                    },
                    {
                        "symbol": "SOL",
                        "price": "850000.00",
                    },
                ]
            }
        }
    )

    prices: list[MarketPriceResponse]