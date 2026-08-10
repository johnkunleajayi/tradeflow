from decimal import Decimal

import pytest

from app.services.providers.quidax_execution_provider import (
    QuidaxExecutionProvider,
)


class FakeQuidaxClient:
    """
    Fake Quidax client used to test order execution.

    No real HTTP requests are made to Quidax.

    The fake simulates the real execution lifecycle:

        POST /users/me/orders
            ↓
        order created
            ↓
        GET /users/me/orders/{order_id}
            ↓
        status = done
            ↓
        executed_volume + avg_price
    """

    def __init__(self):
        self.requests = []

        self.order = {
            "id": "test-order-123",
            "market": "btcngn",
            "side": "buy",
            "ord_type": "market",
            "status": "done",
            "executed_volume": {
                "amount": "0.00011111",
                "currency": "btc",
            },
            "avg_price": {
                "amount": "90000000",
                "currency": "ngn",
            },
        }

        self.order_poll_interval = 0
        self.order_timeout = 1

    def post(
        self,
        endpoint,
        json=None,
        *,
        authenticated=False,
    ):
        self.requests.append(
            {
                "method": "POST",
                "endpoint": endpoint,
                "json": json,
                "authenticated": authenticated,
            }
        )

        return {
            "status": "success",
            "message": "Order created successfully",
            "data": {
                "id": "test-order-123",
            },
        }

    def get(
        self,
        endpoint,
        params=None,
        *,
        authenticated=False,
    ):
        self.requests.append(
            {
                "method": "GET",
                "endpoint": endpoint,
                "params": params,
                "authenticated": authenticated,
            }
        )

        return {
            "status": "success",
            "message": "Successful",
            "data": self.order,
        }


@pytest.fixture
def client():
    return FakeQuidaxClient()


@pytest.fixture
def provider(client):
    return QuidaxExecutionProvider(client=client)


def test_buy_btc_creates_correct_quidax_order(provider, client):
    """
    BUY should convert the NGN amount into BTC quantity
    and send the correct Quidax order.
    """

    result = provider.buy(
        symbol="BTC",
        amount=Decimal("10000"),
        price=Decimal("90000000"),
    )

    assert result["symbol"] == "BTC"
    assert result["side"] == "BUY"

    # Actual execution returned by Quidax.
    assert result["quantity"] == Decimal("0.00011111")
    assert result["price"] == Decimal("90000000")
    assert result["amount"] == (
        Decimal("0.00011111") * Decimal("90000000")
    )

    assert client.requests[0] == {
        "method": "POST",
        "endpoint": "/users/me/orders",
        "json": {
            "market": "btcngn",
            "side": "buy",
            "ord_type": "market",
            "volume": str(
                Decimal("10000") / Decimal("90000000")
            ),
        },
        "authenticated": True,
    }

    assert client.requests[1] == {
        "method": "GET",
        "endpoint": "/users/me/orders/test-order-123",
        "params": None,
        "authenticated": True,
    }


def test_buy_uses_actual_quidax_execution_price(provider):
    """
    TradeFlow should use Quidax's actual average execution price,
    not the estimated price supplied to the provider.
    """

    result = provider.buy(
        symbol="BTC",
        amount=Decimal("10000"),
        price=Decimal("85000000"),
    )

    assert result["price"] == Decimal("90000000")
    assert result["quantity"] == Decimal("0.00011111")


def test_buy_uses_actual_quidax_execution_quantity(provider):
    """
    TradeFlow should use Quidax's actual executed quantity,
    not the originally requested quantity.
    """

    result = provider.buy(
        symbol="BTC",
        amount=Decimal("10000"),
        price=Decimal("90000000"),
    )

    assert result["quantity"] == Decimal("0.00011111")

    requested_quantity = (
        Decimal("10000") / Decimal("90000000")
    )

    assert result["quantity"] != requested_quantity


def test_buy_eth_uses_eth_market(provider, client):
    """
    ETH BUY should use the Quidax ETH/NGN market.
    """

    client.order["market"] = "ethngn"

    provider.buy(
        symbol="ETH",
        amount=Decimal("10000"),
        price=Decimal("5000000"),
    )

    assert client.requests[0]["json"]["market"] == "ethngn"
    assert client.requests[0]["json"]["side"] == "buy"
    assert client.requests[0]["json"]["ord_type"] == "market"


def test_buy_sol_uses_sol_market(provider, client):
    """
    SOL BUY should use the Quidax SOL/NGN market.
    """

    client.order["market"] = "solngn"

    provider.buy(
        symbol="SOL",
        amount=Decimal("10000"),
        price=Decimal("100000"),
    )

    assert client.requests[0]["json"]["market"] == "solngn"


def test_buy_is_case_insensitive(provider, client):
    """
    Lowercase symbols should work exactly like uppercase symbols.
    """

    result = provider.buy(
        symbol="btc",
        amount=Decimal("10000"),
        price=Decimal("90000000"),
    )

    assert result["symbol"] == "BTC"
    assert client.requests[0]["json"]["market"] == "btcngn"


def test_sell_btc_creates_correct_quidax_order(provider, client):
    """
    SELL should send the requested crypto quantity to Quidax.
    """

    quantity = Decimal("0.0001")
    price = Decimal("90000000")

    client.order.update(
        {
            "market": "btcngn",
            "side": "sell",
            "executed_volume": {
                "amount": str(quantity),
                "currency": "btc",
            },
            "avg_price": {
                "amount": str(price),
                "currency": "ngn",
            },
        }
    )

    result = provider.sell(
        symbol="BTC",
        quantity=quantity,
        price=price,
    )

    assert result["symbol"] == "BTC"
    assert result["side"] == "SELL"
    assert result["quantity"] == quantity
    assert result["price"] == price
    assert result["amount"] == quantity * price

    assert client.requests[0] == {
        "method": "POST",
        "endpoint": "/users/me/orders",
        "json": {
            "market": "btcngn",
            "side": "sell",
            "ord_type": "market",
            "volume": str(quantity),
        },
        "authenticated": True,
    }

    assert client.requests[1] == {
        "method": "GET",
        "endpoint": "/users/me/orders/test-order-123",
        "params": None,
        "authenticated": True,
    }


def test_sell_uses_actual_execution_details(provider, client):
    """
    SELL should use the actual executed quantity and average
    execution price returned by Quidax.
    """

    client.order.update(
        {
            "market": "btcngn",
            "side": "sell",
            "executed_volume": {
                "amount": "0.00009500",
                "currency": "btc",
            },
            "avg_price": {
                "amount": "90100000",
                "currency": "ngn",
            },
        }
    )

    result = provider.sell(
        symbol="BTC",
        quantity=Decimal("0.0001"),
        price=Decimal("90000000"),
    )

    assert result["quantity"] == Decimal("0.00009500")
    assert result["price"] == Decimal("90100000")
    assert result["amount"] == (
        Decimal("0.00009500") * Decimal("90100000")
    )


def test_sell_is_case_insensitive(provider, client):
    """
    Lowercase symbols should work exactly like uppercase symbols.
    """

    provider.sell(
        symbol="btc",
        quantity=Decimal("0.0001"),
        price=Decimal("90000000"),
    )

    assert client.requests[0]["json"]["market"] == "btcngn"


def test_unsupported_symbol_raises_error(provider):
    """
    Unsupported symbols should not create an order.
    """

    with pytest.raises(
        ValueError,
        match="Unsupported trading symbol: DOGE",
    ):
        provider.buy(
            symbol="DOGE",
            amount=Decimal("10000"),
            price=Decimal("100"),
        )


def test_buy_returns_completed_quidax_response(provider):
    """
    The completed Quidax order should be preserved in the
    provider response.
    """

    result = provider.buy(
        symbol="BTC",
        amount=Decimal("10000"),
        price=Decimal("90000000"),
    )

    assert result["response"] == {
        "id": "test-order-123",
        "market": "btcngn",
        "side": "buy",
        "ord_type": "market",
        "status": "done",
        "executed_volume": {
            "amount": "0.00011111",
            "currency": "btc",
        },
        "avg_price": {
            "amount": "90000000",
            "currency": "ngn",
        },
    }


def test_buy_returns_order_id(provider):
    """
    The Quidax order ID should be exposed by the provider.
    """

    result = provider.buy(
        symbol="BTC",
        amount=Decimal("10000"),
        price=Decimal("90000000"),
    )

    assert result["order_id"] == "test-order-123"


def test_buy_returns_completed_status(provider):
    """
    The provider should return the final Quidax order status.
    """

    result = provider.buy(
        symbol="BTC",
        amount=Decimal("10000"),
        price=Decimal("90000000"),
    )

    assert result["status"] == "done"


def test_provider_waits_for_completed_order(provider, client):
    """
    The provider must perform both the order creation request
    and the follow-up order-status request.
    """

    provider.buy(
        symbol="BTC",
        amount=Decimal("10000"),
        price=Decimal("90000000"),
    )

    methods = [
        request["method"]
        for request in client.requests
    ]

    assert methods == ["POST", "GET"]