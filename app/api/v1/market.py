from fastapi import APIRouter

from app.schemas.market import (
    MarketPriceResponse,
    MarketPricesResponse,
)
from app.services.market_data_service import (
    MarketDataService,
)

router = APIRouter(tags=["Market"])

service = MarketDataService()


@router.get(
    "/market/prices",
    response_model=MarketPricesResponse,
)
def get_market_prices():
    """
    Returns the latest prices for all supported assets.
    """

    return MarketPricesResponse(
        prices=service.get_all_prices(),
    )


@router.get(
    "/market/prices/{symbol}",
    response_model=MarketPriceResponse,
)
def get_market_price(
    symbol: str,
):
    """
    Returns the latest price for a single asset.
    """

    return service.get_price(symbol)