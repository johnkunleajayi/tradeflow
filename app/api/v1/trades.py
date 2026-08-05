from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.schemas.trade import (
    BuyTradeResponse,
    SellTradeResponse,
    TradeResponse,
)
from app.schemas.trade_request import (
    BuyTradeRequest,
    SellTradeRequest,
)
from app.services.trade_service import TradeService


router = APIRouter(tags=["Trades"])


@router.get(
    "/trades",
    response_model=list[TradeResponse],
)
def get_trades(
    db: Session = Depends(get_db),
):
    """
    Returns all executed trades.
    """

    service = TradeService(db)

    return service.get_trades()


@router.post(
    "/trades/buy",
    response_model=BuyTradeResponse,
)
def buy_trade(
    request: BuyTradeRequest,
    db: Session = Depends(get_db),
):
    """
    Executes a paper BUY trade.
    """

    service = TradeService(db)

    return service.buy(
        symbol=request.symbol,
        amount=request.amount,
    )


@router.post(
    "/trades/sell",
    response_model=SellTradeResponse,
)
def sell_trade(
    request: SellTradeRequest,
    db: Session = Depends(get_db),
):
    """
    Executes a paper SELL trade.
    """

    service = TradeService(db)

    return service.sell(
        symbol=request.symbol,
        quantity=request.quantity,
    )