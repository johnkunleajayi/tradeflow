from decimal import Decimal


def test_get_portfolio_returns_initial_cash(client):
    """
    A new portfolio should contain the default paper wallet
    with no holdings.
    """

    response = client.get("/api/v1/portfolio")

    assert response.status_code == 200

    data = response.json()

    assert Decimal(data["cash_balance"]) == Decimal("100000.00")
    assert Decimal(data["holdings_value"]) == Decimal("0.00")
    assert Decimal(data["total_portfolio_value"]) == Decimal(
        "100000.00"
    )
    assert data["assets"] == []


def test_portfolio_reflects_buy_trade(client):
    """
    A BUY should reduce cash and add the purchased asset
    to the portfolio.
    """

    buy_response = client.post(
        "/api/v1/trades/buy",
        json={
            "symbol": "BTC",
            "amount": "10000.00",
        },
    )

    assert buy_response.status_code == 200

    response = client.get("/api/v1/portfolio")

    assert response.status_code == 200

    data = response.json()

    assert Decimal(data["cash_balance"]) == Decimal(
        "90000.00"
    )

    assert Decimal(data["holdings_value"]) == Decimal(
        "9999.36"
    )

    assert Decimal(data["total_portfolio_value"]) == Decimal(
        "99999.36"
    )

    assert len(data["assets"]) == 1

    asset = data["assets"][0]

    assert asset["symbol"] == "BTC"

    assert Decimal(asset["quantity"]) == Decimal(
        "0.00005952"
    )

    assert Decimal(asset["average_buy_price"]) == Decimal(
        "168000000.00"
    )

    assert Decimal(asset["current_price"]) == Decimal(
        "168000000.00"
    )

    assert Decimal(asset["market_value"]) == Decimal(
        "9999.36"
    )


def test_portfolio_reflects_sell_trade(client):
    """
    Selling the entire holding should remove the asset
    and return the proceeds to cash.
    """

    buy_response = client.post(
        "/api/v1/trades/buy",
        json={
            "symbol": "BTC",
            "amount": "10000.00",
        },
    )

    assert buy_response.status_code == 200

    sell_response = client.post(
        "/api/v1/trades/sell",
        json={
            "symbol": "BTC",
            "quantity": "0.00005952",
        },
    )

    assert sell_response.status_code == 200

    response = client.get("/api/v1/portfolio")

    assert response.status_code == 200

    data = response.json()

    assert Decimal(data["cash_balance"]) == Decimal(
        "99999.36"
    )

    assert Decimal(data["holdings_value"]) == Decimal(
        "0.00"
    )

    assert Decimal(data["total_portfolio_value"]) == Decimal(
        "99999.36"
    )

    assert data["assets"] == []


def test_portfolio_values_multiple_assets(client):
    """
    Portfolio valuation should correctly combine multiple
    supported assets.
    """

    btc_response = client.post(
        "/api/v1/trades/buy",
        json={
            "symbol": "BTC",
            "amount": "10000.00",
        },
    )

    assert btc_response.status_code == 200

    eth_response = client.post(
        "/api/v1/trades/buy",
        json={
            "symbol": "ETH",
            "amount": "20000.00",
        },
    )

    assert eth_response.status_code == 200

    response = client.get("/api/v1/portfolio")

    assert response.status_code == 200

    data = response.json()

    assert Decimal(data["cash_balance"]) == Decimal(
        "70000.00"
    )

    assert Decimal(data["holdings_value"]) == Decimal(
    "29999.34"
)

    assert Decimal(data["total_portfolio_value"]) == Decimal(
    "99999.34"
)

    assert len(data["assets"]) == 2


def test_portfolio_uses_current_market_price(client):
    """
    Portfolio market value should be calculated from the
    current market price rather than the average buy price.
    """

    buy_response = client.post(
        "/api/v1/trades/buy",
        json={
            "symbol": "BTC",
            "amount": "10000.00",
        },
    )

    assert buy_response.status_code == 200

    response = client.get("/api/v1/portfolio")

    assert response.status_code == 200

    data = response.json()

    asset = data["assets"][0]

    quantity = Decimal(asset["quantity"])
    current_price = Decimal(asset["current_price"])
    market_value = Decimal(asset["market_value"])

    assert market_value == quantity * current_price