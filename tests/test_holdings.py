from decimal import Decimal

from app.models.holding import Holding
from app.models.wallet import Wallet
from app.core.constants import WalletType


def test_get_holdings_returns_empty_list_when_no_holdings_exist(client):
    """
    A new test database should have no holdings.
    """

    response = client.get("/api/v1/holdings")

    assert response.status_code == 200
    assert response.json() == []


def test_get_holdings_returns_existing_holding(client, db_session):
    """
    The holdings endpoint should return persisted holdings.
    """

    wallet = Wallet(
        name="Paper Wallet",
        wallet_type=WalletType.PAPER,
        cash_balance=Decimal("100000.00"),
        is_active=True,
    )

    db_session.add(wallet)
    db_session.commit()
    db_session.refresh(wallet)

    holding = Holding(
        wallet_id=wallet.id,
        symbol="BTC",
        quantity=Decimal("0.00250000"),
        average_buy_price=Decimal("168000000.00"),
    )

    db_session.add(holding)
    db_session.commit()
    db_session.refresh(holding)

    response = client.get("/api/v1/holdings")

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1

    result = data[0]

    assert result["id"] == holding.id
    assert result["wallet_id"] == wallet.id
    assert result["symbol"] == "BTC"
    assert Decimal(result["quantity"]) == Decimal("0.00250000")
    assert Decimal(result["average_buy_price"]) == Decimal(
        "168000000.00"
    )

    assert "created_at" in result
    assert "updated_at" in result


def test_get_holdings_returns_multiple_assets(client, db_session):
    """
    The holdings endpoint should return multiple assets
    belonging to the portfolio.
    """

    wallet = Wallet(
        name="Paper Wallet",
        wallet_type=WalletType.PAPER,
        cash_balance=Decimal("100000.00"),
        is_active=True,
    )

    db_session.add(wallet)
    db_session.commit()
    db_session.refresh(wallet)

    holdings = [
        Holding(
            wallet_id=wallet.id,
            symbol="BTC",
            quantity=Decimal("0.00250000"),
            average_buy_price=Decimal("168000000.00"),
        ),
        Holding(
            wallet_id=wallet.id,
            symbol="ETH",
            quantity=Decimal("1.50000000"),
            average_buy_price=Decimal("5200000.00"),
        ),
        Holding(
            wallet_id=wallet.id,
            symbol="SOL",
            quantity=Decimal("10.00000000"),
            average_buy_price=Decimal("850000.00"),
        ),
    ]

    db_session.add_all(holdings)
    db_session.commit()

    response = client.get("/api/v1/holdings")

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 3

    symbols = {item["symbol"] for item in data}

    assert symbols == {"BTC", "ETH", "SOL"}