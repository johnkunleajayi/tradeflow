from fastapi import APIRouter, Depends

from app.schemas.market import (
    MarketPriceResponse,
    MarketPricesResponse,
)
from app.services.market_data_service import (
    MarketDataService,
)

router = APIRouter(tags=["Market"])


def get_market_data_service() -> MarketDataService:
    """
    Creates a market data service for the current request.

    The service is created at request time rather than module
    import time so that the current MARKET_PROVIDER setting
    is always respected.
    """

    return MarketDataService()


@router.get(
    "/market/prices",
    response_model=MarketPricesResponse,
)
def get_market_prices(
    service: MarketDataService = Depends(
        get_market_data_service
    ),
):
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
    service: MarketDataService = Depends(
        get_market_data_service
    ),
):
    """
    Returns the latest price for a single asset.
    """

    return service.get_price(symbol)