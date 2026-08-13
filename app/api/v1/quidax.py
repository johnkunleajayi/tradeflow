from fastapi import APIRouter

from app.schemas.quidax import QuidaxBalancesResponse
from app.services.quidax_account_service import (
    QuidaxAccountService,
)

router = APIRouter(
    tags=["Quidax"]
)


@router.get(
    "/quidax/balances",
    response_model=QuidaxBalancesResponse,
)
def get_quidax_balances():
    """
    Returns live balances from the authenticated Quidax account.

    This endpoint is read-only.

    It does not read or modify TradeFlow's local wallet,
    holdings, or database.
    """

    service = QuidaxAccountService()

    return service.get_balances()