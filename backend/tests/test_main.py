from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.api.v1.routes.market import get_market_data_provider
from app.main import app
from app.providers.market import MarketDataProvider, SymbolNotFoundError
from app.schemas.market import MarketHistory, MarketHistoryPoint, MarketRange, MarketSummary

client = TestClient(app)


class FakeMarketDataProvider(MarketDataProvider):
    def get_summary(self, symbol: str) -> MarketSummary:
        return MarketSummary(
            symbol=symbol,
            company_name=f"{symbol} Test Company",
            price=123.45,
            currency="USD",
            previous_close=120.45,
            change=3.0,
            change_percent=2.5,
            market_state="regular",
            as_of=datetime(2026, 8, 19, 14, 30, tzinfo=UTC),
            source="Test provider",
            is_realtime=False,
            refresh_seconds=15,
        )

    def get_history(self, symbol: str, time_range: MarketRange) -> MarketHistory:
        return MarketHistory(
            symbol=symbol,
            company_name=f"{symbol} Test Company",
            currency="USD",
            range=time_range,
            interval="1m",
            price=123.45,
            baseline_price=120.45,
            change=3.0,
            change_percent=2.5,
            market_state="regular",
            as_of=datetime(2026, 8, 19, 14, 31, tzinfo=UTC),
            points=[
                MarketHistoryPoint(
                    timestamp=datetime(2026, 8, 19, 14, 30, tzinfo=UTC),
                    price=120.45,
                ),
                MarketHistoryPoint(
                    timestamp=datetime(2026, 8, 19, 14, 31, tzinfo=UTC),
                    price=123.45,
                ),
            ],
            source="Test provider",
            is_realtime=False,
            refresh_seconds=15,
        )


@pytest.fixture(autouse=True)
def use_fake_market_data_provider():
    app.dependency_overrides[get_market_data_provider] = lambda: FakeMarketDataProvider()
    yield
    app.dependency_overrides.pop(get_market_data_provider, None)


def test_health_check() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_market_summary_contract() -> None:
    response = client.get("/api/v1/market-summary?symbol=aapl")

    assert response.status_code == 200
    assert response.json() == {
        "symbol": "AAPL",
        "company_name": "AAPL Test Company",
        "price": 123.45,
        "currency": "USD",
        "previous_close": 120.45,
        "change": 3.0,
        "change_percent": 2.5,
        "market_state": "regular",
        "as_of": "2026-08-19T14:30:00Z",
        "source": "Test provider",
        "is_realtime": False,
        "refresh_seconds": 15,
    }


def test_market_history_contract() -> None:
    response = client.get("/api/v1/market-history?symbol=aapl&range=1d")

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "AAPL"
    assert payload["range"] == "1d"
    assert payload["interval"] == "1m"
    assert payload["change"] == 3.0
    assert payload["points"] == [
        {"timestamp": "2026-08-19T14:30:00Z", "price": 120.45},
        {"timestamp": "2026-08-19T14:31:00Z", "price": 123.45},
    ]


def test_invalid_market_history_range_is_rejected() -> None:
    response = client.get("/api/v1/market-history?symbol=AAPL&range=forever")

    assert response.status_code == 422


def test_local_frontend_is_allowed_by_cors() -> None:
    response = client.get(
        "/api/v1/market-summary",
        headers={"Origin": "http://localhost:3000"},
    )

    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_invalid_symbol_is_rejected_before_provider_call() -> None:
    response = client.get("/api/v1/market-summary?symbol=$AAPL")

    assert response.status_code == 422


def test_unknown_symbol_returns_not_found() -> None:
    class MissingSymbolProvider(MarketDataProvider):
        def get_summary(self, symbol: str) -> MarketSummary:
            raise SymbolNotFoundError(f"No market data was found for {symbol}.")

    app.dependency_overrides[get_market_data_provider] = lambda: MissingSymbolProvider()
    response = client.get("/api/v1/market-summary?symbol=NOPE")

    assert response.status_code == 404
    assert response.json() == {"detail": "No market data was found for NOPE."}
