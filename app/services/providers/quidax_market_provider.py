from decimal import Decimal

from app.core.exceptions import UnsupportedSymbolError
from app.integrations.quidax.client import QuidaxClient
from app.services.providers.market_provider import MarketProvider


class QuidaxMarketProvider(MarketProvider):
    """
    Market data provider backed by the Quidax exchange.

    TradeFlow uses simple asset symbols such as BTC, ETH, and SOL,
    while Quidax uses market pairs such as btcngn.

    This provider translates between the two representations.
    """

    SUPPORTED_MARKETS = {
        "BTC": "btcngn",
        "ETH": "ethngn",
        "SOL": "solngn",
    }

    def __init__(
        self,
        client: QuidaxClient | None = None,
    ):
        self.client = client or QuidaxClient()

    def get_supported_symbols(self) -> list[str]:
        """
        Returns the crypto assets currently supported by TradeFlow.
        """

        return list(self.SUPPORTED_MARKETS.keys())

    def get_price(
        self,
        symbol: str,
    ) -> Decimal:
        """
        Returns the latest Quidax market price for an asset.

        Example:

            TradeFlow symbol:
                BTC

            Quidax market:
                btcngn
        """

        symbol = symbol.upper()

        if symbol not in self.SUPPORTED_MARKETS:
            raise UnsupportedSymbolError(symbol)

        market = self.SUPPORTED_MARKETS[symbol]

        response = self.client.get(
            f"/markets/tickers/{market}"
        )

        data = response.get("data", {})
        market_data = data.get(market, {})
        ticker = market_data.get("ticker", {})

        price = ticker.get("last")

        if price is None:
            raise ValueError(
                f"Quidax response did not contain a price "
                f"for {market}."
            )

        return Decimal(str(price))