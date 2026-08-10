from decimal import Decimal


def test_get_all_market_prices(client):
    """
    Returns all prices exposed by the configured market provider.
    """

    response = client.get("/api/v1/market/prices")

    assert response.status_code == 200

    data = response.json()

    assert "prices" in data
    assert len(data["prices"]) == 3

    prices = {
        item["symbol"]: Decimal(item["price"])
        for item in data["prices"]
    }

    assert prices["BTC"] == Decimal("168000000.00")
    assert prices["ETH"] == Decimal("5200000.00")
    assert prices["SOL"] == Decimal("850000.00")


def test_get_single_market_price(client):
    """
    Returns the current price for a specific symbol.
    """

    response = client.get("/api/v1/market/prices/BTC")

    assert response.status_code == 200

    data = response.json()

    assert data["symbol"] == "BTC"
    assert Decimal(data["price"]) == Decimal("168000000.00")


def test_market_price_symbol_is_case_insensitive(client):
    """
    Market symbols should work regardless of input casing.
    """

    response = client.get("/api/v1/market/prices/btc")

    assert response.status_code == 200

    data = response.json()

    assert data["symbol"] == "BTC"
    assert Decimal(data["price"]) == Decimal("168000000.00")


def test_unsupported_market_symbol_returns_error(client):
    """
    An unsupported trading symbol should return HTTP 400.
    """

    response = client.get("/api/v1/market/prices/DOGE")

    assert response.status_code == 400

    data = response.json()

    assert data["detail"] == "Unsupported trading symbol: DOGE"