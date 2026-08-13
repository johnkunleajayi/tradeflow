from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.schemas.automation import (
    AutomationRuleCreateRequest,
    AutomationRuleResponse,
    AutomationStatusResponse,
)
from app.services.automation_service import AutomationService


router = APIRouter(
    prefix="/automation",
    tags=["Automation"],
)


@router.post(
    "/rules",
    response_model=AutomationRuleResponse,
)
def create_automation_rule(
    request: AutomationRuleCreateRequest,
    db: Session = Depends(get_db),
):
    """
    Creates an automated trading rule.
    """

    service = AutomationService(db)

    return service.create_rule(
        symbol=request.symbol,
        price_step=request.price_step,
    )


@router.get(
    "/rules/{symbol}",
    response_model=AutomationRuleResponse,
)
def get_automation_rule(
    symbol: str,
    db: Session = Depends(get_db),
):
    """
    Returns the automation rule for a symbol.
    """

    service = AutomationService(db)

    rule = service.get_rule(symbol)

    if rule is None:
        raise ValueError(
            f"No automation rule exists for {symbol.upper()}."
        )

    return rule


@router.post(
    "/rules/{symbol}/start",
    response_model=AutomationRuleResponse,
)
def start_automation(
    symbol: str,
    db: Session = Depends(get_db),
):
    """
    Activates automation for a symbol.

    If the rule has no reference price, the current
    market price becomes the initial reference.
    """

    service = AutomationService(db)

    return service.activate(symbol)


@router.post(
    "/rules/{symbol}/stop",
    response_model=AutomationRuleResponse,
)
def stop_automation(
    symbol: str,
    db: Session = Depends(get_db),
):
    """
    Stops automation while preserving the reference price.
    """

    service = AutomationService(db)

    return service.deactivate(symbol)


@router.post(
    "/rules/{symbol}/reset",
    response_model=AutomationRuleResponse,
)
def reset_automation(
    symbol: str,
    db: Session = Depends(get_db),
):
    """
    Resets automation to a clean inactive state.

    This clears the persisted reference price and ensures
    automation is inactive.

    The configured price_step is preserved.
    """

    service = AutomationService(db)

    return service.reset(symbol)


@router.get(
    "/rules/{symbol}/status",
    response_model=AutomationStatusResponse,
)
def get_automation_status(
    symbol: str,
    db: Session = Depends(get_db),
):
    """
    Returns current automation status and market price.
    """

    service = AutomationService(db)

    return service.get_status(symbol)