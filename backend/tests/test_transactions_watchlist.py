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
    assert holding["average_cost"] == 166.6667
    assert holding["total_cost"] == 2500

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


def test_fifo_tax_lots_show_the_remaining_purchase_inventory(client: TestClient) -> None:
    register(client)
    record(client, "buy", "AAPL", 10, 100, "2026-01-01T15:00:00Z")
    record(client, "buy", "AAPL", 10, 200, "2026-02-01T15:00:00Z")
    record(client, "sell", "AAPL", 5, 250, "2026-03-01T15:00:00Z")

    inventory = client.get("/api/v1/portfolio/tax-lots")

    assert inventory.status_code == 200
    assert inventory.json()["policy"] == "fifo"
    assert [
        (lot["original_quantity"], lot["remaining_quantity"], lot["cost_per_share"])
        for lot in inventory.json()["lots"]
    ] == [(10, 5, 100), (10, 10, 200)]


def test_voiding_a_trade_preserves_history_and_rebuilds_portfolio(client: TestClient) -> None:
    register(client)
    record(client, "buy", "AAPL", 10, 100, "2026-01-01T15:00:00Z")
    incorrect = record(client, "buy", "AAPL", 5, 200, "2026-02-01T15:00:00Z").json()

    correction = client.post(
        f"/api/v1/portfolio/transactions/{incorrect['transaction']['id']}/void",
        json={"reason": "Quantity entered twice"},
    )

    assert correction.status_code == 200
    body = correction.json()
    assert body["transaction"]["voided_at"] is not None
    assert body["transaction"]["void_reason"] == "Quantity entered twice"
    assert body["portfolio"]["holdings"][0]["quantity"] == 10
    assert body["accounting"]["cash_balance"] == 9000

    history = client.get("/api/v1/portfolio/transactions").json()
    assert len(history) == 2
    assert history[0]["void_reason"] == "Quantity entered twice"
    assert len(client.get("/api/v1/portfolio/tax-lots").json()["lots"]) == 1


def test_voiding_a_buy_is_rejected_when_it_would_create_an_oversell(client: TestClient) -> None:
    register(client)
    purchase = record(client, "buy", "NVDA", 2, 100, "2026-01-01T15:00:00Z").json()
    record(client, "sell", "NVDA", 1, 150, "2026-02-01T15:00:00Z")

    correction = client.post(
        f"/api/v1/portfolio/transactions/{purchase['transaction']['id']}/void",
        json={"reason": "Wrong purchase"},
    )

    assert correction.status_code == 409
    assert correction.json()["detail"] == "Cannot sell NVDA: only 0 shares are available."
    history = client.get("/api/v1/portfolio/transactions").json()
    assert all(transaction["voided_at"] is None for transaction in history)


def test_voiding_a_sale_is_rejected_when_later_cash_would_be_negative(client: TestClient) -> None:
    register(client)
    record(client, "buy", "AAPL", 10, 50, "2026-01-02T15:00:00Z")
    sale = record(client, "sell", "AAPL", 5, 100, "2026-02-01T15:00:00Z").json()
    withdrawal = client.post(
        "/api/v1/portfolio/cash-events",
        json={
            "event_type": "withdrawal",
            "amount": 9800,
            "occurred_at": "2026-03-01T15:00:00Z",
        },
    )
    assert withdrawal.status_code == 201

    correction = client.post(
        f"/api/v1/portfolio/transactions/{sale['transaction']['id']}/void",
        json={"reason": "Wrong sale"},
    )

    assert correction.status_code == 409
    assert correction.json()["detail"].startswith("Insufficient cash:")
    sale_after_rollback = next(
        transaction
        for transaction in client.get("/api/v1/portfolio/transactions").json()
        if transaction["transaction_type"] == "sell"
    )
    assert sale_after_rollback["voided_at"] is None


def test_users_cannot_correct_another_users_transaction(client: TestClient) -> None:
    register(client)
    purchase = record(client, "buy", "AAPL", 1, 100, "2026-01-01T15:00:00Z").json()

    with TestClient(client.app) as another_client:
        register(another_client, "different@example.com")
        response = another_client.post(
            f"/api/v1/portfolio/transactions/{purchase['transaction']['id']}/void",
            json={"reason": "Not my transaction"},
        )

    assert response.status_code == 404


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
