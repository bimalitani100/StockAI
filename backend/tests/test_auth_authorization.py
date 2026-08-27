from datetime import timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.main import app
from app.models.audit import AdminAuditLog
from app.models.cash_event import CashEvent, CashEventType
from app.models.corporate_action import CorporateAction, CorporateActionType
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
            quantity=Decimal("12"),
            average_cost=Decimal("70.25"),
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
    database.add(
        CorporateAction(
            portfolio_id=portfolio.id,
            symbol="NVDA",
            action_type=CorporateActionType.STOCK_SPLIT,
            new_shares=Decimal("2"),
            old_shares=Decimal("1"),
            occurred_at=target.created_at + timedelta(days=1),
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
    assert portfolio_response.json()["corporate_actions"][0]["action_type"] == "stock_split"
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


def test_user_can_update_name_but_not_email_through_profile_settings(
    client: TestClient,
) -> None:
    client.post(
        "/api/v1/auth/register",
        json={"full_name": "Original Name", "email": "profile@example.com", "password": PASSWORD},
    )

    response = client.patch("/api/v1/auth/me", json={"full_name": "  Updated   Investor  "})

    assert response.status_code == 200
    assert response.json()["user"]["full_name"] == "Updated Investor"
    assert client.get("/api/v1/auth/me").json()["user"]["full_name"] == "Updated Investor"
    forbidden_email_change = client.patch(
        "/api/v1/auth/me",
        json={"full_name": "Updated Investor", "email": "changed@example.com"},
    )
    assert forbidden_email_change.status_code == 422


def test_browser_cors_preflight_allows_profile_patch(client: TestClient) -> None:
    response = client.options(
        "/api/v1/auth/me",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "PATCH",
        },
    )

    assert response.status_code == 200
    assert "PATCH" in response.headers["access-control-allow-methods"]


def test_password_change_requires_current_password_and_updates_login(
    client: TestClient,
) -> None:
    email = "password-settings@example.com"
    new_password = "ChangedAI456!"
    client.post(
        "/api/v1/auth/register",
        json={"full_name": "Password User", "email": email, "password": PASSWORD},
    )

    wrong_password = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "WrongPassword!", "new_password": new_password},
    )
    assert wrong_password.status_code == 400
    assert wrong_password.json()["detail"] == "Current password is incorrect."

    changed = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": PASSWORD, "new_password": new_password},
    )
    assert changed.status_code == 204

    client.post("/api/v1/auth/logout")
    old_login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    new_login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": new_password},
    )
    assert old_login.status_code == 401
    assert new_login.status_code == 200
