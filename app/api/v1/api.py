from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.api.v1.holdings import router as holdings_router
from app.api.v1.market import router as market_router
from app.api.v1.portfolio import router as portfolio_router
from app.api.v1.quidax import router as quidax_router
from app.api.v1.trades import router as trades_router
from app.api.v1.trading import router as trading_router
from app.api.v1.wallet import router as wallet_router


api_router = APIRouter()


api_router.include_router(health_router)

api_router.include_router(wallet_router)

api_router.include_router(holdings_router)

api_router.include_router(portfolio_router)

api_router.include_router(market_router)

api_router.include_router(trades_router)

api_router.include_router(quidax_router)

api_router.include_router(trading_router)