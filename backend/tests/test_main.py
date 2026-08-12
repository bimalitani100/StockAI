from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check() -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_market_summary_contract() -> None:
    response = client.get("/api/v1/market-summary")
    assert response.status_code == 200
    assert response.json()["symbol"] == "NVDA"
