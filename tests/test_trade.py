from decimal import Decimal


def test_get_trades_returns_empty_list_initially(client):
    """
    A clean test database should have no executed trades.
    """

    response = client.get("/api/v1/trades")

    assert response.status_code == 200
    assert response.json() == []


def test_buy_trade_executes_successfully(client):
    """
    A valid BUY should deduct cash, create a holding,
    and record a BUY trade.
    """

    response = client.post(
        "/api/v1/trades/buy",
        json={
            "symbol": "BTC",
            "amount": "10000.00",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["symbol"] == "BTC"
    assert Decimal(data["amount"]) == Decimal("10000.00")
    assert Decimal(data["price"]) == Decimal("168000000.00")

    quantity = Decimal(data["quantity"])

    assert quantity > Decimal("0")


def test_buy_trade_updates_wallet_and_holding(
    client,
    db_session,
):
    """
    A BUY should update both wallet cash and the BTC holding.
    """

    response = client.post(
        "/api/v1/trades/buy",
        json={
            "symbol": "BTC",
            "amount": "10000.00",
        },
    )

    assert response.status_code == 200

    wallet_response = client.get("/api/v1/wallet")

    assert wallet_response.status_code == 200

    wallet = wallet_response.json()

    assert Decimal(wallet["cash_balance"]) == Decimal("90000.00")

    holdings_response = client.get("/api/v1/holdings")

    assert holdings_response.status_code == 200

    holdings = holdings_response.json()

    assert len(holdings) == 1
    assert holdings[0]["symbol"] == "BTC"

    assert Decimal(holdings[0]["quantity"]) == Decimal(
        "0.00005952"
    )

    assert Decimal(
        holdings[0]["average_buy_price"]
    ) == Decimal("168000000.00")


def test_buy_trade_is_recorded(client):
    """
    A successful BUY should create a corresponding trade record.
    """

    response = client.post(
        "/api/v1/trades/buy",
        json={
            "symbol": "BTC",
            "amount": "10000.00",
        },
    )

    assert response.status_code == 200

    trades_response = client.get("/api/v1/trades")

    assert trades_response.status_code == 200

    trades = trades_response.json()

    assert len(trades) == 1

    trade = trades[0]

    assert trade["symbol"] == "BTC"
    assert trade["side"] == "BUY"

    assert Decimal(trade["quantity"]) == Decimal(
        "0.00005952"
    )

    assert Decimal(trade["price"]) == Decimal(
        "168000000.00"
    )

    assert Decimal(trade["total_value"]) == Decimal(
        "10000.00"
    )


def test_sell_trade_executes_successfully(
    client,
):
    """
    A valid SELL should reduce the holding, add cash,
    and record a SELL trade.
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

    data = sell_response.json()

    assert data["symbol"] == "BTC"
    assert Decimal(data["quantity"]) == Decimal(
        "0.00005952"
    )
    assert Decimal(data["price"]) == Decimal(
        "168000000.00"
    )
    assert Decimal(data["amount"]) == Decimal(
        "9999.36000000"
    )


def test_sell_trade_removes_holding_and_adds_cash(
    client,
):
    """
    Selling the entire holding should remove the holding
    and return the sale proceeds to the wallet.
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

    holdings_response = client.get("/api/v1/holdings")

    assert holdings_response.status_code == 200
    assert holdings_response.json() == []

    wallet_response = client.get("/api/v1/wallet")

    assert wallet_response.status_code == 200

    wallet = wallet_response.json()

    assert Decimal(wallet["cash_balance"]) == Decimal(
        "99999.36"
    )


def test_sell_trade_is_recorded(client):
    """
    A successful SELL should create a corresponding trade record.
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

    trades_response = client.get("/api/v1/trades")

    assert trades_response.status_code == 200

    trades = trades_response.json()

    assert len(trades) == 2

    buy_trade = trades[0]
    sell_trade = trades[1]

    assert buy_trade["side"] == "BUY"
    assert sell_trade["side"] == "SELL"

    assert sell_trade["symbol"] == "BTC"

    assert Decimal(
        sell_trade["quantity"]
    ) == Decimal("0.00005952")

    assert Decimal(
        sell_trade["price"]
    ) == Decimal("168000000.00")

    assert Decimal(
        sell_trade["total_value"]
    ) == Decimal("9999.36")


def test_buy_with_insufficient_balance_returns_error(
    client,
):
    """
    BUY should fail when the requested amount exceeds
    the wallet cash balance.
    """

    response = client.post(
        "/api/v1/trades/buy",
        json={
            "symbol": "BTC",
            "amount": "100001.00",
        },
    )

    assert response.status_code == 400

    data = response.json()

    assert data["detail"] == "Insufficient wallet balance."


def test_sell_without_holding_returns_error(client):
    """
    SELL should fail when the wallet has no holding
    for the requested symbol.
    """

    response = client.post(
        "/api/v1/trades/sell",
        json={
            "symbol": "BTC",
            "quantity": "0.00005952",
        },
    )

    assert response.status_code == 404

    data = response.json()

    assert data["detail"] == "No holding found for BTC."


def test_sell_more_than_available_returns_error(client):
    """
    SELL should fail when the requested quantity exceeds
    the available holding.
    """

    buy_response = client.post(
        "/api/v1/trades/buy",
        json={
            "symbol": "BTC",
            "amount": "10000.00",
        },
    )

    assert buy_response.status_code == 200

    response = client.post(
        "/api/v1/trades/sell",
        json={
            "symbol": "BTC",
            "quantity": "1.00000000",
        },
    )

    assert response.status_code == 400

    data = response.json()

    assert data["detail"] == "Insufficient BTC holding."


def test_trade_with_unsupported_symbol_returns_error(
    client,
):
    """
    BUY and SELL should reject unsupported market symbols.
    """

    buy_response = client.post(
        "/api/v1/trades/buy",
        json={
            "symbol": "DOGE",
            "amount": "10000.00",
        },
    )

    assert buy_response.status_code == 400

    assert buy_response.json()["detail"] == (
        "Unsupported trading symbol: DOGE"
    )

    sell_response = client.post(
        "/api/v1/trades/sell",
        json={
            "symbol": "DOGE",
            "quantity": "1.00000000",
        },
    )

    assert sell_response.status_code == 400

    assert sell_response.json()["detail"] == (
        "Unsupported trading symbol: DOGE"
    )