from decimal import Decimal


def test_get_wallet_creates_default_wallet(client):
    """
    A first request should create and return
    the default paper wallet.
    """

    response = client.get("/api/v1/wallet")

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == 1
    assert data["name"] == "Paper Wallet"
    assert data["wallet_type"] == "PAPER"
    assert Decimal(data["cash_balance"]) == Decimal("100000.00")
    assert data["is_active"] is True

    assert "created_at" in data
    assert "updated_at" in data


def test_get_wallet_returns_existing_wallet(client):
    """
    A second request should return the existing active wallet
    rather than creating another wallet.
    """

    first_response = client.get("/api/v1/wallet")
    second_response = client.get("/api/v1/wallet")

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    first_data = first_response.json()
    second_data = second_response.json()

    assert second_data["id"] == first_data["id"]
    assert second_data["name"] == first_data["name"]
    assert second_data["wallet_type"] == first_data["wallet_type"]
    assert second_data["cash_balance"] == first_data["cash_balance"]
    assert second_data["is_active"] is True


def test_wallet_response_has_expected_fields(client):
    """
    Ensures the wallet API response maintains its expected contract.
    """

    response = client.get("/api/v1/wallet")

    assert response.status_code == 200

    data = response.json()

    expected_fields = {
        "id",
        "name",
        "wallet_type",
        "cash_balance",
        "is_active",
        "created_at",
        "updated_at",
    }

    assert expected_fields.issubset(data.keys())