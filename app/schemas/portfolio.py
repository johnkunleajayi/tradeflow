from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PortfolioAssetResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "symbol": "BTC",
                "quantity": "0.00250000",
                "average_buy_price": "168000000.00",
                "current_price": "170500000.00",
                "market_value": "426250.00",
            }
        }
    )

    symbol: str = Field(examples=["BTC"])
    quantity: Decimal = Field(examples=["0.00250000"])
    average_buy_price: Decimal = Field(
        examples=["168000000.00"]
    )
    current_price: Decimal = Field(
        examples=["170500000.00"]
    )
    market_value: Decimal = Field(
        examples=["426250.00"]
    )


class PortfolioResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "cash_balance": "990000.00",
                "holdings_value": "426250.00",
                "total_portfolio_value": "1416250.00",
                "assets": [
                    {
                        "symbol": "BTC",
                        "quantity": "0.00250000",
                        "average_buy_price": "168000000.00",
                        "current_price": "170500000.00",
                        "market_value": "426250.00",
                    }
                ],
            }
        }
    )

    cash_balance: Decimal = Field(
        examples=["990000.00"]
    )

    holdings_value: Decimal = Field(
        examples=["426250.00"]
    )

    total_portfolio_value: Decimal = Field(
        examples=["1416250.00"]
    )

    assets: list[PortfolioAssetResponse]