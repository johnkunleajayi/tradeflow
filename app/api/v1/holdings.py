from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.schemas.holding import HoldingResponse
from app.services.holding_service import HoldingService

router = APIRouter(tags=["Holdings"])


@router.get(
    "/holdings",
    response_model=list[HoldingResponse],
)
def get_holdings(db: Session = Depends(get_db)):
    service = HoldingService(db)

    return service.get_holdings()