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
    Returns all recorded trades.
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
    Executes a BUY trade using the execution provider
    configured by TRADING_MODE.

    PAPER mode:
        Executes against the TradeFlow paper execution provider.

    LIVE mode:
        Executes a real market BUY order through Quidax.
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
    Executes a SELL trade using the execution provider
    configured by TRADING_MODE.

    PAPER mode:
        Executes against the TradeFlow paper execution provider.

    LIVE mode:
        Executes a real market SELL order through Quidax.
    """

    service = TradeService(db)

    return service.sell(
        symbol=request.symbol,
        quantity=request.quantity,
    )