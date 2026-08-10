from app.core.settings import settings
from app.services.providers.execution_provider import ExecutionProvider
from app.services.providers.paper_execution_provider import (
    PaperExecutionProvider,
)
from app.services.providers.quidax_execution_provider import (
    QuidaxExecutionProvider,
)


class ExecutionFactory:
    """
    Creates the configured trade execution provider.

    The execution provider is selected from application settings.

    Examples:

        TRADING_MODE=paper

        TRADING_MODE=live
    """

    @staticmethod
    def create() -> ExecutionProvider:
        """
        Returns the configured execution provider.
        """

        trading_mode = settings.TRADING_MODE.lower()

        if trading_mode == "paper":
            return PaperExecutionProvider()

        if trading_mode == "live":
            return QuidaxExecutionProvider()

        raise ValueError(
            f"Unsupported trading mode: {trading_mode}"
        )