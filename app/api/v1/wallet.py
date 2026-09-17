from fastapi import APIRouter

from app.schemas.quidax import QuidaxBalancesResponse
from app.services.quidax_account_service import (
    QuidaxAccountService,
)


router = APIRouter(tags=["Wallet"])


@router.get(
    "/wallet",
    response_model=QuidaxBalancesResponse,
)
def get_wallet():
    """
    Returns the live authenticated Quidax account balances.

    Quidax is the sole source of truth for available
    cryptocurrency and NGN balances.
    """

    service = QuidaxAccountService()

    return service.get_balances()