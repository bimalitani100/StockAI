from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.api.v1.routes.market import get_market_data_provider
from app.main import app
from app.providers.market import MarketDataProvider, MarketDataUnavailableError
from app.schemas.market import MarketSummary

PASSWORD = "StockAI123!"


class ValuationProvider(MarketDataProvider):
    prices = {"AAPL": 150.0, "NVDA": 200.0}

    def get_summary(self, symbol: str) -> MarketSummary:
        if symbol not in self.prices:
            raise MarketDataUnavailableError(f"No quote is available for {symbol}.")
        return MarketSummary(
            symbol=symbol,
            company_name=f"{symbol} Test Company",
            price=self.prices[symbol],
            currency="USD",
            previous_close=self.prices[symbol] - 1,
            change=1,
            change_percent=1.25,
            market_state="regular",
            as_of=datetime(2026, 8, 19, 15, 0, tzinfo=UTC),
            source="Test provider",
            is_realtime=False,
            refresh_seconds=15,
        )


@pytest.fixture(autouse=True)
def use_valuation_provider():
    app.dependency_overrides[get_market_data_provider] = lambda: ValuationProvider()
    yield
    app.dependency_overrides.pop(get_market_data_provider, None)


def register(client: TestClient, email: str = "accounting@example.com") -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Accounting User", "email": email, "password": PASSWORD},
    )
    assert response.status_code == 201


def cash_event(client: TestClient, event_type: str, amount: float, symbol: str | None = None):
    return client.post(
        "/api/v1/portfolio/cash-events",
        json={
            "event_type": event_type,
            "amount": amount,
            "symbol": symbol,
            "occurred_at": "2026-01-01T12:00:00Z",
        },
    )


def transaction(
    client: TestClient,
    transaction_type: str,
    quantity: float,
    price: float,
    fee: float,
):
    return client.post(
        "/api/v1/portfolio/transactions",
        json={
            "transaction_type": transaction_type,
            "symbol": "AAPL",
            "quantity": quantity,
            "price": price,
            "fee": fee,
            "occurred_at": "2026-02-01T12:00:00Z"
            if transaction_type == "buy"
            else "2026-03-01T12:00:00Z",
        },
    )


def test_fees_cash_and_realized_gain_follow_fifo_cost(client: TestClient) -> None:
    register(client)
    assert cash_event(client, "deposit", 1000).status_code == 201

    purchase = transaction(client, "buy", 4, 100, 4)
    sale = transaction(client, "sell", 1, 150, 2)

    assert purchase.status_code == 201
    assert purchase.json()["portfolio"]["holdings"][0]["average_cost"] == 101
    assert sale.status_code == 201
    assert sale.json()["accounting"] == {
        "cash_balance": 744.0,
        "net_contributions": 1000.0,
        "dividend_income": 0.0,
        "realized_gain": 47.0,
        "trade_fees": 6.0,
    }


def test_fifo_realized_gain_consumes_oldest_lots_first(client: TestClient) -> None:
    register(client)
    assert cash_event(client, "deposit", 10000).status_code == 201
    first = transaction(client, "buy", 10, 100, 10)
    assert first.status_code == 201
    second = client.post(
        "/api/v1/portfolio/transactions",
        json={
            "transaction_type": "buy",
            "symbol": "AAPL",
            "quantity": 10,
            "price": 200,
            "fee": 20,
            "occurred_at": "2026-02-02T12:00:00Z",
        },
    )
    assert second.status_code == 201
    sale = transaction(client, "sell", 12, 300, 12)

    assert sale.status_code == 201
    assert sale.json()["accounting"]["realized_gain"] == 2174
    holding = sale.json()["portfolio"]["holdings"][0]
    assert holding["quantity"] == 8
    assert holding["average_cost"] == 202


def test_insufficient_cash_rolls_back_buy_and_withdrawal(client: TestClient) -> None:
    register(client)
    cash_event(client, "deposit", 100)

    purchase = transaction(client, "buy", 2, 60, 0)
    withdrawal = cash_event(client, "withdrawal", 101)

    assert purchase.status_code == 409
    assert withdrawal.status_code == 409
    assert client.get("/api/v1/portfolio/transactions").json() == []
    assert len(client.get("/api/v1/portfolio/cash-events").json()) == 1


def test_dividend_increases_return_but_not_contributions(client: TestClient) -> None:
    register(client)
    cash_event(client, "deposit", 500)

    dividend = cash_event(client, "dividend", 25, "aapl")

    assert dividend.status_code == 201
    accounting = dividend.json()["accounting"]
    assert accounting["cash_balance"] == 525
    assert accounting["net_contributions"] == 500
    assert accounting["dividend_income"] == 25
    assert cash_event(client, "dividend", 10).status_code == 422
    valuation = client.get("/api/v1/portfolio/valuation").json()
    assert valuation["total_value"] == 525
    assert valuation["total_return"] == 25
    assert valuation["total_return_percent"] == 5


def test_live_valuation_combines_cash_holdings_and_net_contributions(client: TestClient) -> None:
    register(client)
    cash_event(client, "deposit", 1000)
    transaction(client, "buy", 2, 100, 0)

    response = client.get("/api/v1/portfolio/valuation")

    assert response.status_code == 200
    valuation = response.json()
    assert valuation["is_complete"] is True
    assert valuation["holdings_market_value"] == 300
    assert valuation["total_value"] == 1100
    assert valuation["total_return"] == 100
    assert valuation["total_return_percent"] == 10
    assert valuation["holdings"][0]["unrealized_gain"] == 100


def test_valuation_refuses_complete_totals_when_a_quote_is_missing(client: TestClient) -> None:
    register(client)
    cash_event(client, "deposit", 1000)
    client.post(
        "/api/v1/portfolio/transactions",
        json={
            "transaction_type": "buy",
            "symbol": "MISSING",
            "quantity": 1,
            "price": 100,
            "occurred_at": "2026-02-01T12:00:00Z",
        },
    )

    valuation = client.get("/api/v1/portfolio/valuation").json()

    assert valuation["is_complete"] is False
    assert valuation["total_value"] is None
    assert valuation["total_return"] is None
    assert valuation["holdings"][0]["error"] == "No quote is available for MISSING."
