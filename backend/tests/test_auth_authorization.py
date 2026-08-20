from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.main import app
from app.models.audit import AdminAuditLog
from app.models.cash_event import CashEvent, CashEventType
from app.models.portfolio import Holding, Portfolio
from app.models.transaction import PortfolioTransaction, TransactionType
from app.models.user import User, UserRole

PASSWORD = "StockAI123!"


def create_user(database: Session, email: str, role: UserRole = UserRole.USER) -> User:
    user = User(
        email=email,
        full_name="Test User",
        password_hash=hash_password(PASSWORD),
        role=role,
        is_active=True,
    )
    user.portfolios.append(Portfolio(name="Primary Portfolio"))
    database.add(user)
    database.commit()
    database.refresh(user)
    return user


def test_registration_creates_standard_user_and_http_only_session(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"full_name": "New Investor", "email": "Investor@Example.com", "password": PASSWORD},
    )

    assert response.status_code == 201
    assert response.json()["user"]["email"] == "investor@example.com"
    assert response.json()["user"]["role"] == "user"
    assert "HttpOnly" in response.headers["set-cookie"]
    assert client.get("/api/v1/auth/me").status_code == 200


def test_user_transactions_and_portfolio_are_isolated_by_account(client: TestClient) -> None:
    client.post(
        "/api/v1/auth/register",
        json={"full_name": "Portfolio Owner", "email": "owner@example.com", "password": PASSWORD},
    )
    client.post(
        "/api/v1/portfolio/cash-events",
        json={"event_type": "deposit", "amount": 1000},
    )

    response = client.post(
        "/api/v1/portfolio/transactions",
        json={
            "transaction_type": "buy",
            "symbol": "aapl",
            "quantity": 4,
            "price": 190.25,
        },
    )

    assert response.status_code == 201
    assert response.json()["portfolio"]["holdings"][0]["symbol"] == "AAPL"
    assert response.json()["portfolio"]["total_cost"] == 761.0

    with TestClient(app) as another_client:
        another_client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Different Investor",
                "email": "different@example.com",
                "password": PASSWORD,
            },
        )
        other_portfolio = another_client.get("/api/v1/portfolio")
        other_transactions = another_client.get("/api/v1/portfolio/transactions")

    assert other_portfolio.status_code == 200
    assert other_portfolio.json()["holdings"] == []
    assert other_transactions.json() == []


def test_standard_user_is_forbidden_from_admin_data(client: TestClient) -> None:
    client.post(
        "/api/v1/auth/register",
        json={"full_name": "Standard User", "email": "user@example.com", "password": PASSWORD},
    )

    assert client.get("/api/v1/admin/users").status_code == 403


def test_admin_can_view_all_user_holdings_and_access_is_audited(database: Session) -> None:
    admin = create_user(database, "admin@example.com", UserRole.ADMIN)
    target = create_user(database, "investor@example.com")
    portfolio = database.scalar(select(Portfolio).where(Portfolio.user_id == target.id))
    assert portfolio is not None
    database.add(
        Holding(
            portfolio_id=portfolio.id,
            symbol="NVDA",
            quantity=Decimal("6"),
            average_cost=Decimal("140.50"),
        )
    )
    database.add(
        CashEvent(
            portfolio_id=portfolio.id,
            event_type=CashEventType.OPENING_BALANCE,
            amount=Decimal("843"),
            occurred_at=target.created_at,
        )
    )
    database.add(
        PortfolioTransaction(
            portfolio_id=portfolio.id,
            symbol="NVDA",
            transaction_type=TransactionType.OPENING_BALANCE,
            quantity=Decimal("6"),
            price=Decimal("140.50"),
            occurred_at=target.created_at,
        )
    )
    database.commit()

    with TestClient(app) as admin_client:
        login = admin_client.post(
            "/api/v1/auth/login",
            json={"email": admin.email, "password": PASSWORD},
        )
        assert login.status_code == 200

        users = admin_client.get("/api/v1/admin/users")
        portfolio_response = admin_client.get(f"/api/v1/admin/users/{target.id}/portfolio")

    assert users.status_code == 200
    assert len(users.json()) == 2
    assert portfolio_response.status_code == 200
    assert portfolio_response.json()["portfolio"]["holdings"][0]["symbol"] == "NVDA"
    assert portfolio_response.json()["transactions"][0]["symbol"] == "NVDA"
    assert portfolio_response.json()["accounting"]["cash_balance"] == 0
    assert database.scalar(select(func.count(AdminAuditLog.id))) == 1


def test_unauthenticated_portfolio_request_is_rejected(client: TestClient) -> None:
    assert client.get("/api/v1/portfolio").status_code == 401


def test_logout_clears_the_session_cookie(client: TestClient) -> None:
    client.post(
        "/api/v1/auth/register",
        json={"full_name": "Session User", "email": "session@example.com", "password": PASSWORD},
    )

    response = client.post("/api/v1/auth/logout")

    assert response.status_code == 204
    assert "stockai_session=" in response.headers["set-cookie"]
    assert client.get("/api/v1/auth/me").status_code == 401
