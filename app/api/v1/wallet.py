from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.schemas.wallet import WalletResponse
from app.services.wallet_service import WalletService

router = APIRouter(tags=["Wallet"])


@router.get(
    "/wallet",
    response_model=WalletResponse,
)
def get_wallet(db: Session = Depends(get_db)):
    service = WalletService(db)
    return service.get_wallet()