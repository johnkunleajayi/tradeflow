from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_DOWN
from time import monotonic, sleep

from app.core.settings import settings
from app.integrations.quidax.client import QuidaxClient
from app.services.providers.execution_provider import ExecutionProvider
from app.services.providers.quidax_market_provider import (
    QuidaxMarketProvider,
)


class QuidaxExecutionProvider(ExecutionProvider):
    """
    Live trade execution provider backed by Quidax.

    Responsibilities:

    - Send BUY and SELL orders to Quidax.
    - Validate Quidax market trading rules.
    - Normalize order quantities and amounts to Quidax precision.
    - Serialize order values without unnecessary trailing decimals.
    - Wait for order completion.
    - Retrieve actual matched trade fills.
    - Aggregate multiple fills.
    - Calculate actual gross execution value.
    - Apply the configured Quidax trading fee model.
    - Return execution details to the portfolio layer.

    Portfolio state remains the responsibility of the
    trading/portfolio layer.

    Important Quidax behavior:

    A completed order may return:

        status = "done"
        trades = None
        trades_count = "0"

    while the actual matched fill is available through:

        GET /users/me/trades

    Therefore TradeFlow MUST NOT rely on the order's
    `trades_count` field to determine whether a fill exists.

    Quidax market-order semantics:

    BUY:
        The market BUY volume represents the quote currency
        amount to spend.

    SELL:
        The market SELL volume represents the base currency
        quantity to sell.

    Quidax trading rules:

    BUY:
        The quote amount is normalized to quote_precision.
        The amount must satisfy minimum_order_size.

    SELL:
        The base quantity is normalized DOWN to base_precision.
        The estimated quote value must satisfy minimum_order_size.

    Precision is obtained dynamically from Quidax rather than
    being hard-coded for BTC, ETH, or SOL.
    """

    SUPPORTED_MARKETS = {
        "BTC": "btcngn",
        "ETH": "ethngn",
        "SOL": "solngn",
    }

    TERMINAL_SUCCESS_STATUS = "done"

    # Quidax trade timestamps are returned with second-level
    # precision. Allow a small amount of tolerance around the
    # completed order's timestamps when matching fills.
    FILL_TIME_TOLERANCE_SECONDS = 5

    def __init__(
        self,
        client: QuidaxClient | None = None,
    ):
        self.client = client or QuidaxClient()

        # Reuse the same Quidax client for market trading rules.
        self.market_provider = QuidaxMarketProvider(
            client=self.client
        )

    @property
    def fee_rate(self) -> Decimal:
        """
        Current configured Quidax trading fee rate.

        Example:

            0.001

        represents 0.10%.
        """

        return Decimal(
            str(settings.QUIDAX_TRADING_FEE_RATE)
        )

    def _get_market(
        self,
        symbol: str,
    ) -> str:
        """
        Converts a TradeFlow symbol into a Quidax market.
        """

        symbol = symbol.upper()

        try:
            return self.SUPPORTED_MARKETS[symbol]
        except KeyError as exc:
            raise ValueError(
                f"Unsupported trading symbol: {symbol}"
            ) from exc

    def _get_market_rules(
        self,
        symbol: str,
    ) -> dict:
        """
        Returns the current Quidax trading rules for a symbol.

        Rules include:

            base_precision
            quote_precision
            price_precision
            minimum_order_size
        """

        return self.market_provider.get_market_rules(
            symbol
        )

    @staticmethod
    def _quantize_down(
        value: Decimal,
        precision: int,
    ) -> Decimal:
        """
        Quantizes a Decimal DOWN to the requested number of
        decimal places.

        ROUND_DOWN is intentional.

        For SELL orders, TradeFlow must never increase the
        quantity supplied by the user.

        Example:

            0.0000201743 with precision 8

        becomes:

            0.00002017
        """

        if precision < 0:
            raise ValueError(
                "Precision cannot be negative."
            )

        quantum = Decimal("1").scaleb(-precision)

        return value.quantize(
            quantum,
            rounding=ROUND_DOWN,
        )

    @staticmethod
    def _format_order_value(
        value: Decimal,
    ) -> str:
        """
        Converts a normalized Decimal into an exchange-safe
        decimal string.

        This is important because Quidax validates the number
        of decimal places submitted in the request.

        Examples:

            Decimal("10000.00")
                -> "10000"

            Decimal("0.000020170000")
                -> "0.00002017"

            Decimal("100.50")
                -> "100.5"

        Scientific notation is deliberately avoided.
        """

        formatted = format(
            value,
            "f",
        )

        if "." in formatted:
            formatted = formatted.rstrip("0").rstrip(".")

        if formatted in {
            "",
            "-0",
        }:
            return "0"

        return formatted

    def _normalize_buy_amount(
        self,
        symbol: str,
        amount: Decimal,
    ) -> Decimal:
        """
        Normalizes a BUY quote-currency amount according to
        Quidax quote precision.

        Also validates Quidax's minimum order size.
        """

        if amount <= 0:
            raise ValueError(
                "Buy amount must be greater than zero."
            )

        rules = self._get_market_rules(symbol)

        quote_precision = int(
            rules.get(
                "quote_precision",
                2,
            )
        )

        minimum_order_size = Decimal(
            str(
                rules.get(
                    "minimum_order_size",
                    "0",
                )
            )
        )

        normalized_amount = self._quantize_down(
            amount,
            quote_precision,
        )

        if normalized_amount <= 0:
            raise ValueError(
                f"BUY amount for {symbol} becomes zero after "
                f"normalizing to {quote_precision} decimal places."
            )

        if (
            minimum_order_size > 0
            and normalized_amount < minimum_order_size
        ):
            raise ValueError(
                f"BUY amount for {symbol} must be at least "
                f"{minimum_order_size} NGN according to Quidax. "
                f"Requested amount after precision normalization: "
                f"{normalized_amount}"
            )

        return normalized_amount

    def _normalize_sell_quantity(
        self,
        symbol: str,
        quantity: Decimal,
        price: Decimal,
    ) -> Decimal:
        """
        Normalizes a SELL base-asset quantity according to
        Quidax base precision.

        Also validates the estimated quote value against
        Quidax's minimum order size.

        The quantity is always rounded DOWN so TradeFlow
        never submits more than the requested quantity.
        """

        if quantity <= 0:
            raise ValueError(
                "Sell quantity must be greater than zero."
            )

        if price <= 0:
            raise ValueError(
                "Sell price must be greater than zero."
            )

        rules = self._get_market_rules(symbol)

        base_precision = int(
            rules.get(
                "base_precision",
                8,
            )
        )

        minimum_order_size = Decimal(
            str(
                rules.get(
                    "minimum_order_size",
                    "0",
                )
            )
        )

        normalized_quantity = self._quantize_down(
            quantity,
            base_precision,
        )

        if normalized_quantity <= 0:
            raise ValueError(
                f"SELL quantity for {symbol} becomes zero after "
                f"normalizing to {base_precision} decimal places."
            )

        estimated_quote_value = (
            normalized_quantity * price
        )

        if (
            minimum_order_size > 0
            and estimated_quote_value < minimum_order_size
        ):
            raise ValueError(
                f"SELL order for {symbol} is below Quidax's "
                f"minimum order value of {minimum_order_size} NGN. "
                f"Estimated order value: "
                f"{estimated_quote_value}"
            )

        return normalized_quantity

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
        Polls Quidax until the order reaches a successful
        terminal state.

        A `done` status does not itself prove that TradeFlow
        has obtained the actual execution fill.

        The caller subsequently retrieves the actual
        matched trades.
        """

        started_at = monotonic()

        while True:
            response = self.client.get(
                f"/users/me/orders/{order_id}",
                authenticated=True,
            )

            order = self._extract_order_data(
                response
            )

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

            sleep(
                self.client.order_poll_interval
            )

    @staticmethod
    def _to_decimal(
        value: object,
    ) -> Decimal:
        """
        Safely converts a Quidax numeric value to Decimal.
        """

        try:
            return Decimal(str(value))
        except Exception as exc:
            raise ValueError(
                "Invalid numeric value returned by Quidax: "
                f"{value!r}"
            ) from exc

    @staticmethod
    def _parse_datetime(
        value: object,
    ) -> datetime | None:
        """
        Parses a Quidax ISO timestamp.
        """

        if not value:
            return None

        try:
            parsed = datetime.fromisoformat(
                str(value).replace(
                    "Z",
                    "+00:00",
                )
            )

            if parsed.tzinfo is None:
                parsed = parsed.replace(
                    tzinfo=timezone.utc
                )

            return parsed

        except (TypeError, ValueError):
            return None

    def _get_order_fills(
        self,
        completed_order: dict,
    ) -> list[dict]:
        """
        Retrieves the actual matched trade fills belonging
        to the completed Quidax order.

        Quidax may return fills directly through:

            completed_order["trades"]

        If those are unavailable, TradeFlow queries:

            GET /users/me/trades

        `trades_count` is deliberately NOT used as a prerequisite
        for querying the trades endpoint.
        """

        # ---------------------------------------------------------
        # 1. Prefer trades embedded directly in the order.
        # ---------------------------------------------------------

        direct_trades = completed_order.get(
            "trades"
        )

        if isinstance(
            direct_trades,
            list,
        ):
            valid_direct_trades = [
                trade
                for trade in direct_trades
                if isinstance(trade, dict)
            ]

            if valid_direct_trades:
                return valid_direct_trades

        # ---------------------------------------------------------
        # 2. Fall back to the authenticated user trades endpoint.
        # ---------------------------------------------------------

        market_data = completed_order.get(
            "market",
            {},
        )

        if not isinstance(
            market_data,
            dict,
        ):
            raise RuntimeError(
                "Quidax completed order returned invalid market data."
            )

        market = str(
            market_data.get(
                "id",
                "",
            )
        ).lower()

        if not market:
            raise RuntimeError(
                "Quidax completed order did not contain "
                "a valid market."
            )

        order_created_at = self._parse_datetime(
            completed_order.get(
                "created_at"
            )
        )

        order_updated_at = self._parse_datetime(
            completed_order.get(
                "updated_at"
            )
        )

        order_done_at = self._parse_datetime(
            completed_order.get(
                "done_at"
            )
        )

        order_end_at = (
            order_done_at
            or order_updated_at
            or order_created_at
        )

        response = self.client.get(
            "/users/me/trades",
            params={
                "market": market,
                "limit": 100,
            },
            authenticated=True,
        )

        data = response.get("data")

        if not isinstance(
            data,
            list,
        ):
            raise RuntimeError(
                "Quidax trades endpoint returned invalid trade data."
            )

        candidate_trades: list[dict] = []

        for trade in data:
            if not isinstance(
                trade,
                dict,
            ):
                continue

            trade_market_data = trade.get(
                "market",
                {},
            )

            if not isinstance(
                trade_market_data,
                dict,
            ):
                continue

            trade_market = str(
                trade_market_data.get(
                    "id",
                    "",
                )
            ).lower()

            if trade_market != market:
                continue

            trade_created_at = self._parse_datetime(
                trade.get(
                    "created_at"
                )
            )

            if trade_created_at is None:
                continue

            if order_created_at is not None:
                lower_bound = (
                    order_created_at
                    - timedelta(
                        seconds=self.FILL_TIME_TOLERANCE_SECONDS
                    )
                )

                if trade_created_at < lower_bound:
                    continue

            if order_end_at is not None:
                upper_bound = (
                    order_end_at
                    + timedelta(
                        seconds=self.FILL_TIME_TOLERANCE_SECONDS
                    )
                )

                if trade_created_at > upper_bound:
                    continue

            candidate_trades.append(
                trade
            )

        if not candidate_trades:
            raise RuntimeError(
                "Quidax order is marked done, but TradeFlow "
                "could not locate a matching execution fill "
                "through /users/me/trades. "
                f"Market: {market}, "
                f"Order ID: {completed_order.get('id')}"
            )

        candidate_trades.sort(
            key=lambda trade: (
                self._parse_datetime(
                    trade.get("created_at")
                )
                or datetime.min.replace(
                    tzinfo=timezone.utc
                )
            )
        )

        return candidate_trades

    def _aggregate_fills(
        self,
        fills: list[dict],
        symbol: str,
    ) -> dict:
        """
        Aggregates one or more Quidax trade fills.

        Returns:

            quantity
            total quote value
            weighted-average execution price
            fills
        """

        expected_market = self._get_market(
            symbol
        )

        total_quantity = Decimal("0")
        total_value = Decimal("0")

        valid_fills: list[dict] = []

        for fill in fills:
            market = fill.get(
                "market",
                {},
            )

            if not isinstance(
                market,
                dict,
            ):
                continue

            market_id = str(
                market.get(
                    "id",
                    "",
                )
            ).lower()

            if market_id != expected_market:
                continue

            price_data = fill.get(
                "price",
                {},
            )

            volume_data = fill.get(
                "volume",
                {},
            )

            total_data = fill.get(
                "total",
                {},
            )

            if not isinstance(
                price_data,
                dict,
            ):
                continue

            if not isinstance(
                volume_data,
                dict,
            ):
                continue

            if not isinstance(
                total_data,
                dict,
            ):
                continue

            price = self._to_decimal(
                price_data.get(
                    "amount",
                    "0",
                )
            )

            quantity = self._to_decimal(
                volume_data.get(
                    "amount",
                    "0",
                )
            )

            total = self._to_decimal(
                total_data.get(
                    "amount",
                    "0",
                )
            )

            if price <= 0:
                continue

            if quantity <= 0:
                continue

            if total <= 0:
                continue

            total_quantity += quantity
            total_value += total

            valid_fills.append(
                fill
            )

        if not valid_fills:
            raise RuntimeError(
                f"Quidax returned no valid {symbol} "
                "trade fills for the completed order."
            )

        if total_quantity <= 0:
            raise RuntimeError(
                "Quidax fills produced zero executed quantity."
            )

        if total_value <= 0:
            raise RuntimeError(
                "Quidax fills produced zero execution value."
            )

        average_price = (
            total_value / total_quantity
        )

        return {
            "quantity": total_quantity,
            "amount": total_value,
            "price": average_price,
            "fills": valid_fills,
        }

    def _get_actual_execution(
        self,
        order_response: dict,
        side: str,
        symbol: str,
    ) -> dict:
        """
        Resolves the actual completed execution from Quidax.

        Actual trade fills are authoritative for:

        - executed quantity
        - execution price
        - gross execution value

        The configured fee model is then applied.

        SELL:
            Fee is deducted from quote-currency proceeds.

        BUY:
            Fee is deducted from the acquired base asset.
        """

        order = self._extract_order_data(
            order_response
        )

        order_id = order.get(
            "id"
        )

        if not order_id:
            raise ValueError(
                "Quidax order response did not contain "
                "an order ID."
            )

        completed_order = self._wait_for_order(
            str(order_id)
        )

        fills = self._get_order_fills(
            completed_order
        )

        execution = self._aggregate_fills(
            fills=fills,
            symbol=symbol,
        )

        gross_quantity = execution[
            "quantity"
        ]

        gross_amount = execution[
            "amount"
        ]

        price = execution[
            "price"
        ]

        side = side.upper()

        market_data = completed_order.get(
            "market",
            {},
        )

        if not isinstance(
            market_data,
            dict,
        ):
            market_data = {}

        base_currency = str(
            market_data.get(
                "base_unit",
                symbol,
            )
        ).upper()

        quote_currency = str(
            market_data.get(
                "quote_unit",
                "NGN",
            )
        ).upper()

        fee_rate = self.fee_rate

        if fee_rate < 0:
            raise ValueError(
                "Quidax trading fee rate cannot be negative."
            )

        # ---------------------------------------------------------
        # SELL
        # ---------------------------------------------------------

        if side == "SELL":

            fee = (
                gross_amount
                * fee_rate
            )

            net_amount = (
                gross_amount
                - fee
            )

            if net_amount <= 0:
                raise ValueError(
                    f"Quidax order {order_id} produced "
                    "non-positive net proceeds."
                )

            return {
                "order_id": str(
                    order_id
                ),
                "status": str(
                    completed_order.get(
                        "status",
                        "",
                    )
                ),
                "symbol": symbol.upper(),
                "side": "SELL",
                "quantity": gross_quantity,
                "gross_quantity": gross_quantity,
                "price": price,
                "amount": net_amount,
                "gross_amount": gross_amount,
                "net_amount": net_amount,
                "fee": fee,
                "fee_currency": quote_currency,
                "fee_rate": fee_rate,
                "fills": execution[
                    "fills"
                ],
                "order": completed_order,
            }

        # ---------------------------------------------------------
        # BUY
        # ---------------------------------------------------------

        if side == "BUY":

            # Gross cryptocurrency received from actual fills.
            #
            # Fee is charged against the acquired base asset.
            #
            # The quote amount remains the actual gross cash
            # value of the matched trade.

            fee = (
                gross_quantity
                * fee_rate
            )

            net_quantity = (
                gross_quantity
                - fee
            )

            if net_quantity <= 0:
                raise ValueError(
                    f"Quidax order {order_id} produced "
                    "non-positive net quantity."
                )

            return {
                "order_id": str(
                    order_id
                ),
                "status": str(
                    completed_order.get(
                        "status",
                        "",
                    )
                ),
                "symbol": symbol.upper(),
                "side": "BUY",
                "quantity": net_quantity,
                "gross_quantity": gross_quantity,
                "price": price,
                "amount": gross_amount,
                "gross_amount": gross_amount,
                "net_amount": gross_amount,
                "fee": fee,
                "fee_currency": base_currency,
                "fee_rate": fee_rate,
                "fills": execution[
                    "fills"
                ],
                "order": completed_order,
            }

        raise ValueError(
            f"Unsupported execution side: {side}"
        )

    def buy(
        self,
        symbol: str,
        amount: Decimal,
        price: Decimal,
    ) -> dict:
        """
        Places a market BUY order on Quidax.

        `amount` represents the quote-currency amount
        TradeFlow wants to spend.

        The amount is normalized according to the current
        Quidax quote precision and minimum order size.

        Quidax remains authoritative for the actual
        cryptocurrency quantity received.

        IMPORTANT:

        Market BUY orders do not send `price`.
        Quidax requires `volume` for the market order.
        """

        symbol = symbol.upper()

        if amount <= 0:
            raise ValueError(
                "Buy amount must be greater than zero."
            )

        if price <= 0:
            raise ValueError(
                "Buy price must be greater than zero."
            )

        # Quidax is authoritative for current market rules.
        normalized_amount = (
            self._normalize_buy_amount(
                symbol=symbol,
                amount=amount,
            )
        )

        market = self._get_market(
            symbol
        )

        # IMPORTANT:
        #
        # Do not send:
        #
        #     str(normalized_amount)
        #
        # directly.
        #
        # A Decimal such as:
        #
        #     Decimal("10000.00")
        #
        # can otherwise become:
        #
        #     "10000.00"
        #
        # when Quidax expects:
        #
        #     "10000"
        #
        # The numeric value is the same, but the decimal
        # representation can violate Quidax's precision rule.

        order_volume = self._format_order_value(
            normalized_amount
        )

        response = self.client.post(
            "/users/me/orders",
            json={
                "market": market,
                "side": "buy",
                "ord_type": "market",
                "volume": order_volume,
            },
            authenticated=True,
        )

        execution = self._get_actual_execution(
            response,
            side="BUY",
            symbol=symbol,
        )

        return {
            "symbol": symbol,
            "side": "BUY",
            "amount": execution[
                "amount"
            ],
            "gross_amount": execution[
                "gross_amount"
            ],
            "net_amount": execution[
                "net_amount"
            ],
            "price": execution[
                "price"
            ],
            "quantity": execution[
                "quantity"
            ],
            "gross_quantity": execution[
                "gross_quantity"
            ],
            "fee": execution[
                "fee"
            ],
            "fee_currency": execution[
                "fee_currency"
            ],
            "fee_rate": execution[
                "fee_rate"
            ],
            "order_id": execution[
                "order_id"
            ],
            "status": execution[
                "status"
            ],
            "fills": execution[
                "fills"
            ],
            "response": execution[
                "order"
            ],
        }

    def sell(
        self,
        symbol: str,
        quantity: Decimal,
        price: Decimal,
    ) -> dict:
        """
        Places a market SELL order on Quidax.

        `quantity` represents the base cryptocurrency
        quantity TradeFlow wants to sell.

        The quantity is normalized DOWN according to the
        current Quidax base precision.

        Quidax remains authoritative for the actual
        executed quantity and gross proceeds.
        """

        symbol = symbol.upper()

        if quantity <= 0:
            raise ValueError(
                "Sell quantity must be greater than zero."
            )

        if price <= 0:
            raise ValueError(
                "Sell price must be greater than zero."
            )

        normalized_quantity = (
            self._normalize_sell_quantity(
                symbol=symbol,
                quantity=quantity,
                price=price,
            )
        )

        market = self._get_market(
            symbol
        )

        order_volume = self._format_order_value(
            normalized_quantity
        )

        response = self.client.post(
            "/users/me/orders",
            json={
                "market": market,
                "side": "sell",
                "ord_type": "market",
                "volume": order_volume,
            },
            authenticated=True,
        )

        execution = self._get_actual_execution(
            response,
            side="SELL",
            symbol=symbol,
        )

        return {
            "symbol": symbol,
            "side": "SELL",
            "amount": execution[
                "amount"
            ],
            "gross_amount": execution[
                "gross_amount"
            ],
            "net_amount": execution[
                "net_amount"
            ],
            "price": execution[
                "price"
            ],
            "quantity": execution[
                "quantity"
            ],
            "gross_quantity": execution[
                "gross_quantity"
            ],
            "fee": execution[
                "fee"
            ],
            "fee_currency": execution[
                "fee_currency"
            ],
            "fee_rate": execution[
                "fee_rate"
            ],
            "order_id": execution[
                "order_id"
            ],
            "status": execution[
                "status"
            ],
            "fills": execution[
                "fills"
            ],
            "response": execution[
                "order"
            ],
        }