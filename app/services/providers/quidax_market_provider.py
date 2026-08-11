from decimal import Decimal

from app.core.exceptions import UnsupportedSymbolError
from app.integrations.quidax.client import QuidaxClient
from app.services.providers.market_provider import MarketProvider


class QuidaxMarketProvider(MarketProvider):
    """
    Market data provider backed by Quidax.
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
        return list(self.SUPPORTED_MARKETS.keys())

    def _get_market_id(
        self,
        symbol: str,
    ) -> str:

        symbol = symbol.upper()

        if symbol not in self.SUPPORTED_MARKETS:
            raise UnsupportedSymbolError(symbol)

        return self.SUPPORTED_MARKETS[symbol]

    def get_market_rules(
        self,
        symbol: str,
    ) -> dict:
        """
        Returns Quidax trading rules.

        Example:
        {
            "base_precision": 8,
            "quote_precision": 2,
            "price_precision": 0,
            "minimum_order_size": Decimal("1250")
        }
        """

        market = self._get_market_id(symbol)

        response = self.client.get("/markets")

        markets = response.get("data", [])

        market_data = next(
            (
                item
                for item in markets
                if item.get("id") == market
            ),
            None,
        )

        if market_data is None:
            raise ValueError(
                f"Market {market} not found."
            )

        rules = market_data.get(
            "trading_rules",
            {},
        )

        return {
            "base_precision": int(
                rules.get("base_precision", 8)
            ),
            "quote_precision": int(
                rules.get("quote_precision", 2)
            ),
            "price_precision": int(
                rules.get("price_precision", 2)
            ),
            "minimum_order_size": Decimal(
                str(
                    rules.get(
                        "minimum_order_size",
                        "0",
                    )
                )
            ),
        }

    def get_price(
        self,
        symbol: str,
    ) -> Decimal:

        market = self._get_market_id(symbol)

        response = self.client.get(
            f"/markets/tickers/{market}"
        )

        data = response.get("data", {})
        market_data = data.get(market, {})
        ticker = market_data.get("ticker", {})

        price = ticker.get("last")

        if price is None:
            raise ValueError(
                f"No price found for {market}"
            )

        return Decimal(str(price))