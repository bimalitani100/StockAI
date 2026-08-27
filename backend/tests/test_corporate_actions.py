from fastapi.testclient import TestClient

PASSWORD = "StockAI123!"


def register(client: TestClient, email: str = "splits@example.com") -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Split Investor", "email": email, "password": PASSWORD},
    )
    assert response.status_code == 201
    deposit = client.post(
        "/api/v1/portfolio/cash-events",
        json={
            "event_type": "deposit",
            "amount": 10000,
            "occurred_at": "2026-01-01T12:00:00Z",
        },
    )
    assert deposit.status_code == 201


def trade(
    client: TestClient,
    transaction_type: str,
    quantity: float,
    price: float,
    occurred_at: str,
):
    return client.post(
        "/api/v1/portfolio/transactions",
        json={
            "transaction_type": transaction_type,
            "symbol": "AAPL",
            "quantity": quantity,
            "price": price,
            "occurred_at": occurred_at,
        },
    )


def split(
    client: TestClient,
    new_shares: float,
    old_shares: float,
    occurred_at: str = "2026-03-01T12:00:00Z",
):
    return client.post(
        "/api/v1/portfolio/corporate-actions/stock-splits",
        json={
            "symbol": "AAPL",
            "new_shares": new_shares,
            "old_shares": old_shares,
            "occurred_at": occurred_at,
        },
    )


def test_forward_split_changes_shares_but_preserves_cost_and_cash(client: TestClient) -> None:
    register(client)
    trade(client, "buy", 10, 100, "2026-02-01T12:00:00Z")
    cash_before = client.get("/api/v1/portfolio/accounting").json()["cash_balance"]

    response = split(client, 2, 1)

    assert response.status_code == 201
    holding = response.json()["portfolio"]["holdings"][0]
    assert holding["quantity"] == 20
    assert holding["average_cost"] == 50
    assert holding["total_cost"] == 1000
    assert client.get("/api/v1/portfolio/accounting").json()["cash_balance"] == cash_before

    inventory = client.get("/api/v1/portfolio/tax-lots").json()["lots"][0]
    assert inventory["original_quantity"] == 10
    assert inventory["adjusted_quantity"] == 20
    assert inventory["remaining_quantity"] == 20
    assert inventory["cost_per_share"] == 50
    assert inventory["cost_basis"] == 1000


def test_reverse_split_preserves_fractional_shares_and_cost_basis(client: TestClient) -> None:
    register(client)
    trade(client, "buy", 10, 100, "2026-02-01T12:00:00Z")

    response = split(client, 1, 4)

    assert response.status_code == 201
    holding = response.json()["portfolio"]["holdings"][0]
    assert holding["quantity"] == 2.5
    assert holding["average_cost"] == 400
    assert holding["total_cost"] == 1000


def test_split_after_partial_sale_adjusts_only_remaining_inventory(client: TestClient) -> None:
    register(client)
    trade(client, "buy", 10, 100, "2026-02-01T12:00:00Z")
    trade(client, "sell", 4, 150, "2026-02-15T12:00:00Z")

    response = split(client, 2, 1)

    holding = response.json()["portfolio"]["holdings"][0]
    assert holding["quantity"] == 12
    assert holding["average_cost"] == 50
    assert holding["total_cost"] == 600
    accounting = client.get("/api/v1/portfolio/accounting").json()
    assert accounting["realized_gain"] == 200


def test_sale_after_split_uses_split_adjusted_fifo_cost(client: TestClient) -> None:
    register(client)
    trade(client, "buy", 10, 100, "2026-02-01T12:00:00Z")
    split(client, 2, 1)

    sale = trade(client, "sell", 15, 60, "2026-04-01T12:00:00Z")

    assert sale.status_code == 201
    holding = sale.json()["portfolio"]["holdings"][0]
    assert holding["quantity"] == 5
    assert holding["average_cost"] == 50
    assert sale.json()["accounting"]["realized_gain"] == 150


def test_split_without_shares_is_rejected_without_history(client: TestClient) -> None:
    register(client)

    response = split(client, 2, 1)

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Cannot apply a stock split for AAPL: no shares were held at that time."
    )
    assert client.get("/api/v1/portfolio/corporate-actions").json() == []


def test_backdated_split_before_purchase_is_rejected(client: TestClient) -> None:
    register(client)
    trade(client, "buy", 10, 100, "2026-03-01T12:00:00Z")

    response = split(client, 2, 1, "2026-02-01T12:00:00Z")

    assert response.status_code == 409
    assert client.get("/api/v1/portfolio").json()["holdings"][0]["quantity"] == 10


def test_voiding_split_rebuilds_original_position_and_preserves_history(client: TestClient) -> None:
    register(client)
    trade(client, "buy", 10, 100, "2026-02-01T12:00:00Z")
    action = split(client, 2, 1).json()["corporate_action"]

    correction = client.post(
        f"/api/v1/portfolio/corporate-actions/{action['id']}/void",
        json={"reason": "Split ratio entered incorrectly"},
    )

    assert correction.status_code == 200
    assert correction.json()["portfolio"]["holdings"][0]["quantity"] == 10
    corrected = correction.json()["corporate_action"]
    assert corrected["voided_at"] is not None
    assert corrected["void_reason"] == "Split ratio entered incorrectly"
    history = client.get("/api/v1/portfolio/corporate-actions").json()
    assert history[0]["voided_at"] is not None


def test_voiding_split_is_rejected_when_later_sale_requires_adjusted_shares(
    client: TestClient,
) -> None:
    register(client)
    trade(client, "buy", 10, 100, "2026-02-01T12:00:00Z")
    action = split(client, 2, 1).json()["corporate_action"]
    trade(client, "sell", 15, 60, "2026-04-01T12:00:00Z")

    correction = client.post(
        f"/api/v1/portfolio/corporate-actions/{action['id']}/void",
        json={"reason": "Attempt unsafe correction"},
    )

    assert correction.status_code == 409
    assert correction.json()["detail"] == "Cannot sell AAPL: only 10 shares are available."
    history = client.get("/api/v1/portfolio/corporate-actions").json()
    assert history[0]["voided_at"] is None


def test_users_cannot_void_another_users_corporate_action(client: TestClient) -> None:
    register(client)
    trade(client, "buy", 10, 100, "2026-02-01T12:00:00Z")
    action_id = split(client, 2, 1).json()["corporate_action"]["id"]

    with TestClient(client.app) as another_client:
        register(another_client, "different-splits@example.com")
        response = another_client.post(
            f"/api/v1/portfolio/corporate-actions/{action_id}/void",
            json={"reason": "Not my action"},
        )

    assert response.status_code == 404


def test_one_for_one_split_is_rejected_as_meaningless(client: TestClient) -> None:
    register(client)
    trade(client, "buy", 10, 100, "2026-02-01T12:00:00Z")

    response = split(client, 1, 1)

    assert response.status_code == 422


def test_split_that_exceeds_fractional_precision_is_rejected(client: TestClient) -> None:
    register(client)
    trade(client, "buy", 10, 100, "2026-02-01T12:00:00Z")

    response = split(client, 1, 3)

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Cannot apply the stock split for AAPL: it creates shares beyond StockAI's "
        "6-decimal precision. Cash-in-lieu is not supported yet."
    )
    assert client.get("/api/v1/portfolio/corporate-actions").json() == []
