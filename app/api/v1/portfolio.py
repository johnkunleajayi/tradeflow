from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.schemas.portfolio import PortfolioResponse
from app.services.portfolio_query_service import (
    PortfolioQueryService,
)

router = APIRouter(tags=["Portfolio"])


@router.get(
    "/portfolio",
    response_model=PortfolioResponse,
)
def get_portfolio(
    db: Session = Depends(get_db),
):
    """
    Returns the current portfolio summary.

    Includes:

    - Cash balance
    - Current holdings
    - Current market prices
    - Market value of each holding
    - Total holdings value
    - Total portfolio value
    """

    service = PortfolioQueryService(db)

    return service.get_portfolio()