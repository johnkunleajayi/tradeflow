from decimal import Decimal
from time import monotonic, sleep

from app.integrations.quidax.client import QuidaxClient
from app.services.providers.execution_provider import ExecutionProvider


class QuidaxExecutionProvider(ExecutionProvider):
    """
    Live trade execution provider backed by Quidax.

    This provider is responsible only for:
    - Sending BUY and SELL orders to Quidax.
    - Waiting for the order to reach a completed state.
    - Reading the actual execution details from Quidax.

    Portfolio state remains the responsibility of the trading layer.
    """

    SUPPORTED_MARKETS = {
        "BTC": "btcngn",
        "ETH": "ethngn",
        "SOL": "solngn",
    }

    TERMINAL_SUCCESS_STATUS = "done"

    def __init__(
        self,
        client: QuidaxClient | None = None,
    ):
        self.client = client or QuidaxClient()

    def _get_market(self, symbol: str) -> str:
        """
        Converts a TradeFlow symbol into its Quidax market pair.
        """

        symbol = symbol.upper()

        try:
            return self.SUPPORTED_MARKETS[symbol]
        except KeyError as exc:
            raise ValueError(
                f"Unsupported trading symbol: {symbol}"
            ) from exc

    def _extract_order_data(
        self,
        response: dict,
    ) -> dict:
        """
        Extracts the order object from a Quidax response.
        """

        data = response.get("data")

        if not isinstance(data, dict):
            raise ValueError(
                "Quidax response did not contain valid order data."
            )

        return data

    def _wait_for_order(
        self,
        order_id: str,
    ) -> dict:
        """
        Polls Quidax until the order reaches a terminal state.

        Successful execution requires status='done'.

        If the order does not complete within the configured
        timeout, an exception is raised rather than allowing
        TradeFlow to record an uncertain execution.
        """

        started_at = monotonic()

        while True:
            response = self.client.get(
                f"/users/me/orders/{order_id}",
                authenticated=True,
            )

            order = self._extract_order_data(response)

            status = str(
                order.get("status", "")
            ).lower()

            if status == self.TERMINAL_SUCCESS_STATUS:
                return order

            elapsed = monotonic() - started_at

            if elapsed >= self.client.order_timeout:
                raise RuntimeError(
                    "Quidax order did not complete within "
                    f"{self.client.order_timeout} seconds. "
                    f"Order ID: {order_id}, status: {status}"
                )

            sleep(self.client.order_poll_interval)

    def _get_actual_execution(
        self,
        order_response: dict,
    ) -> dict:
        """
        Resolves the actual completed execution from Quidax.

        Quidax may return the order immediately after creation,
        so the order is fetched again until it is completed.
        """

        order = self._extract_order_data(order_response)

        order_id = order.get("id")

        if not order_id:
            raise ValueError(
                "Quidax order response did not contain an order ID."
            )

        completed_order = self._wait_for_order(
            str(order_id)
        )

        executed_volume = completed_order.get(
            "executed_volume",
            {},
        )

        avg_price = completed_order.get(
            "avg_price",
            {},
        )

        quantity = Decimal(
            str(
                executed_volume.get(
                    "amount",
                    "0",
                )
            )
        )

        price = Decimal(
            str(
                avg_price.get(
                    "amount",
                    "0",
                )
            )
        )

        if quantity <= 0:
            raise ValueError(
                f"Quidax order {order_id} completed without "
                "an executed volume."
            )

        if price <= 0:
            raise ValueError(
                f"Quidax order {order_id} completed without "
                "a valid average execution price."
            )

        amount = quantity * price

        return {
            "order_id": str(order_id),
            "status": str(
                completed_order.get("status", "")
            ),
            "quantity": quantity,
            "price": price,
            "amount": amount,
            "order": completed_order,
        }

    def buy(
        self,
        symbol: str,
        amount: Decimal,
        price: Decimal,
    ) -> dict:
        """
        Places a market BUY order on Quidax.

        The supplied price is only used to estimate the amount
        of base currency to request.

        Quidax remains authoritative for the actual:
        - executed quantity
        - average execution price
        - total execution value
        """

        symbol = symbol.upper()

        market = self._get_market(symbol)

        requested_quantity = amount / price

        response = self.client.post(
            "/users/me/orders",
            json={
                "market": market,
                "side": "buy",
                "ord_type": "market",
                "volume": str(requested_quantity),
            },
            authenticated=True,
        )

        execution = self._get_actual_execution(
            response
        )

        return {
            "symbol": symbol,
            "side": "BUY",
            "amount": execution["amount"],
            "price": execution["price"],
            "quantity": execution["quantity"],
            "order_id": execution["order_id"],
            "status": execution["status"],
            "response": execution["order"],
        }

    def sell(
        self,
        symbol: str,
        quantity: Decimal,
        price: Decimal,
    ) -> dict:
        """
        Places a market SELL order on Quidax.

        The requested quantity is sent to Quidax.

        Quidax remains authoritative for the actual:
        - executed quantity
        - average execution price
        - total execution value
        """

        symbol = symbol.upper()

        market = self._get_market(symbol)

        response = self.client.post(
            "/users/me/orders",
            json={
                "market": market,
                "side": "sell",
                "ord_type": "market",
                "volume": str(quantity),
            },
            authenticated=True,
        )

        execution = self._get_actual_execution(
            response
        )

        return {
            "symbol": symbol,
            "side": "SELL",
            "amount": execution["amount"],
            "price": execution["price"],
            "quantity": execution["quantity"],
            "order_id": execution["order_id"],
            "status": execution["status"],
            "response": execution["order"],
        }