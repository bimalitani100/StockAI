from fastapi.testclient import TestClient

PASSWORD = "StockAI123!"


def register(client: TestClient, email: str = "investor@example.com") -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Test Investor", "email": email, "password": PASSWORD},
    )
    assert response.status_code == 201
    deposit = client.post(
        "/api/v1/portfolio/cash-events",
        json={
            "event_type": "deposit",
            "amount": 10000,
            "occurred_at": "2025-01-01T15:00:00Z",
        },
    )
    assert deposit.status_code == 201


def record(
    client: TestClient,
    transaction_type: str,
    symbol: str,
    quantity: float,
    price: float,
    occurred_at: str,
):
    return client.post(
        "/api/v1/portfolio/transactions",
        json={
            "transaction_type": transaction_type,
            "symbol": symbol,
            "quantity": quantity,
            "price": price,
            "occurred_at": occurred_at,
        },
    )


def test_buys_and_sells_rebuild_current_holdings(client: TestClient) -> None:
    register(client)

    assert record(client, "buy", "aapl", 10, 100, "2026-01-01T15:00:00Z").status_code == 201
    second_buy = record(client, "buy", "AAPL", 10, 200, "2026-02-01T15:00:00Z")
    sale = record(client, "sell", "AAPL", 5, 250, "2026-03-01T15:00:00Z")

    assert second_buy.status_code == 201
    assert sale.status_code == 201
    holding = sale.json()["portfolio"]["holdings"][0]
    assert holding["quantity"] == 15
    assert holding["average_cost"] == 150
    assert holding["total_cost"] == 2250

    transactions = client.get("/api/v1/portfolio/transactions").json()
    assert [transaction["transaction_type"] for transaction in transactions] == [
        "sell",
        "buy",
        "buy",
    ]


def test_oversell_is_rejected_without_changing_history(client: TestClient) -> None:
    register(client)
    record(client, "buy", "NVDA", 2, 140, "2026-01-01T15:00:00Z")

    response = record(client, "sell", "NVDA", 3, 150, "2026-02-01T15:00:00Z")

    assert response.status_code == 409
    assert response.json()["detail"] == "Cannot sell NVDA: only 2 shares are available."
    assert len(client.get("/api/v1/portfolio/transactions").json()) == 1
    assert client.get("/api/v1/portfolio").json()["holdings"][0]["quantity"] == 2


def test_backdated_oversell_is_rejected_by_chronological_rebuild(client: TestClient) -> None:
    register(client)
    record(client, "buy", "MSFT", 4, 400, "2026-02-01T15:00:00Z")

    response = record(client, "sell", "MSFT", 1, 410, "2026-01-01T15:00:00Z")

    assert response.status_code == 409
    assert len(client.get("/api/v1/portfolio/transactions").json()) == 1


def test_watchlist_is_idempotent_and_private(client: TestClient) -> None:
    register(client)

    assert client.put("/api/v1/watchlist/items/aapl").status_code == 200
    repeated = client.put("/api/v1/watchlist/items/AAPL")

    assert [item["symbol"] for item in repeated.json()["items"]] == ["AAPL"]

    with TestClient(client.app) as another_client:
        register(another_client, "different@example.com")
        assert another_client.get("/api/v1/watchlist").json()["items"] == []

    removed = client.delete("/api/v1/watchlist/items/AAPL")
    assert removed.status_code == 200
    assert removed.json()["items"] == []
