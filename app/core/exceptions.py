from fastapi import HTTPException, status


class TradeFlowException(HTTPException):
    """
    Base exception for all TradeFlow API errors.
    """

    def __init__(self, status_code: int, detail: str):
        super().__init__(
            status_code=status_code,
            detail=detail,
        )


class WalletNotFoundError(TradeFlowException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active wallet found.",
        )


class InsufficientBalanceError(TradeFlowException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient wallet balance.",
        )


class InsufficientHoldingError(TradeFlowException):
    def __init__(self, symbol: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient {symbol.upper()} holding.",
        )


class HoldingNotFoundError(TradeFlowException):
    def __init__(self, symbol: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No holding found for {symbol.upper()}.",
        )


class UnsupportedSymbolError(TradeFlowException):
    def __init__(self, symbol: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported trading symbol: {symbol.upper()}",
        )