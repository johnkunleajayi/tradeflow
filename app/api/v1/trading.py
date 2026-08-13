from fastapi import APIRouter

from app.core.settings import settings
from app.services.providers.execution_factory import ExecutionFactory


router = APIRouter(
    tags=["Trading"],
)


@router.get(
    "/trading/status",
)
def get_trading_status():
    """
    Returns the currently configured trading mode
    and execution provider.

    This endpoint is read-only.

    It does not execute trades and does not modify
    the database or exchange.
    """

    trading_mode = settings.TRADING_MODE.lower()

    execution_provider = ExecutionFactory.create()

    return {
        "trading_mode": trading_mode,
        "execution_provider": (
            execution_provider.__class__.__name__
        ),
        "live_trading": trading_mode == "live",
    }