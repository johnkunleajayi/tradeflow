from decimal import Decimal

import pytest

from app.core.exceptions import UnsupportedSymbolError
from app.services.providers.quidax_market_provider import (
    QuidaxMarketProvider,
)


class FakeQuidaxClient:
    """
    Fake Quidax client used for testing.

    This prevents pytest from making real HTTP requests
    to the Quidax API.
    """

    RESPONSES = {
        "/markets/tickers/btcngn": {
            "status": "success",
            "message": "Successful",
            "data": {
                "btcngn": {
                    "ticker": {
                        "high": "91126539",
                        "vol": "0.63054777",
                        "last": 90621907.0,
                        "low": "90000672",
                        "buy": 90215060,
                        "sell": 90622046,
                        "open": "90000672",
                    },
                    "at": 1786355405000,
                }
            },
        },
        "/markets/tickers/ethngn": {
            "status": "success",
            "message": "Successful",
            "data": {
                "ethngn": {
                    "ticker": {
                        "high": "2700000",
                        "vol": "10.50",
                        "last": 2674903.0,
                        "low": "2600000",
                        "buy": 2670000,
                        "sell": 2674903,
                        "open": "2650000",
                    },
                    "at": 1786355405000,
                }
            },
        },
        "/markets/tickers/solngn": {
            "status": "success",
            "message": "Successful",
            "data": {
                "solngn": {
                    "ticker": {
                        "high": "108000",
                        "vol": "100.25",
                        "last": 107004.34,
                        "low": "105000",
                        "buy": 106900,
                        "sell": 107004.34,
                        "open": "106000",
                    },
                    "at": 1786355405000,
                }
            },
        },
    }

    def __init__(self):
        self.requests = []

    def get(self, endpoint, params=None):
        self.requests.append(
            {
                "endpoint": endpoint,
                "params": params,
            }
        )

        return self.RESPONSES[endpoint]


@pytest.fixture
def provider():
    """
    Creates a QuidaxMarketProvider using the fake client.
    """

    client = FakeQuidaxClient()

    return QuidaxMarketProvider(client=client)


def test_get_supported_symbols(provider):
    """
    Provider should expose all supported TradeFlow symbols.
    """

    symbols = provider.get_supported_symbols()

    assert symbols == ["BTC", "ETH", "SOL"]


def test_get_btc_price(provider):
    """
    Provider should correctly extract the BTC price.
    """

    price = provider.get_price("BTC")

    assert price == Decimal("90621907.0")


def test_get_eth_price(provider):
    """
    Provider should correctly extract the ETH price.
    """

    price = provider.get_price("ETH")

    assert price == Decimal("2674903.0")


def test_get_sol_price(provider):
    """
    Provider should correctly extract the SOL price.
    """

    price = provider.get_price("SOL")

    assert price == Decimal("107004.34")


def test_symbol_is_case_insensitive(provider):
    """
    Lowercase symbols should work exactly like uppercase symbols.
    """

    price = provider.get_price("btc")

    assert price == Decimal("90621907.0")


def test_unsupported_symbol_raises_error(provider):
    """
    Unsupported symbols should raise the standard TradeFlow error.
    """

    with pytest.raises(UnsupportedSymbolError):
        provider.get_price("DOGE")


def test_provider_uses_correct_quidax_market(provider):
    """
    TradeFlow BTC should map to the Quidax BTC/NGN market.
    """

    provider.get_price("BTC")

    assert provider.client.requests == [
        {
            "endpoint": "/markets/tickers/btcngn",
            "params": None,
        }
    ]


def test_provider_does_not_make_real_http_request(provider):
    """
    The provider test must use the fake client rather than
    making an actual request to Quidax.
    """

    provider.get_price("ETH")

    assert provider.client.requests[0]["endpoint"] == (
        "/markets/tickers/ethngn"
    )