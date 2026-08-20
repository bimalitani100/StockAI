from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select

from app.core.security import hash_password
from app.database.session import SessionLocal
from app.models.cash_event import CashEvent, CashEventType
from app.models.portfolio import Holding, Portfolio
from app.models.transaction import PortfolioTransaction, TransactionType
from app.models.user import User, UserRole
from app.models.watchlist import Watchlist, WatchlistItem

DEMO_PASSWORD = "StockAI123!"


def ensure_user(email: str, full_name: str, role: UserRole) -> User:
    with SessionLocal() as database:
        user = database.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(
                email=email,
                full_name=full_name,
                password_hash=hash_password(DEMO_PASSWORD),
                role=role,
                is_active=True,
            )
            user.portfolios.append(Portfolio(name="Primary Portfolio"))
            database.add(user)
            database.commit()
            database.refresh(user)
        watchlist = database.scalar(select(Watchlist).where(Watchlist.user_id == user.id))
        if watchlist is None:
            database.add(Watchlist(user_id=user.id, name="My Watchlist"))
            database.commit()
        return user


def ensure_opening_position(user_email: str, symbol: str, quantity: str, price: str) -> None:
    with SessionLocal() as database:
        user = database.scalar(select(User).where(User.email == user_email))
        if user is None:
            raise RuntimeError(f"Seed user {user_email} was not created.")
        portfolio = database.scalar(select(Portfolio).where(Portfolio.user_id == user.id))
        if portfolio is None:
            raise RuntimeError(f"Seed portfolio for {user_email} was not created.")
        holding = database.scalar(
            select(Holding).where(
                Holding.portfolio_id == portfolio.id,
                Holding.symbol == symbol,
            )
        )
        if holding is None:
            occurred_at = datetime.now(UTC)
            database.add(
                Holding(
                    portfolio_id=portfolio.id,
                    symbol=symbol,
                    quantity=Decimal(quantity),
                    average_cost=Decimal(price),
                )
            )
            database.add(
                PortfolioTransaction(
                    portfolio_id=portfolio.id,
                    symbol=symbol,
                    transaction_type=TransactionType.OPENING_BALANCE,
                    quantity=Decimal(quantity),
                    price=Decimal(price),
                    occurred_at=occurred_at,
                )
            )
            database.add(
                CashEvent(
                    portfolio_id=portfolio.id,
                    event_type=CashEventType.OPENING_BALANCE,
                    amount=Decimal(quantity) * Decimal(price),
                    occurred_at=occurred_at,
                )
            )
            database.commit()


def ensure_watchlist_item(user_email: str, symbol: str) -> None:
    with SessionLocal() as database:
        user = database.scalar(select(User).where(User.email == user_email))
        if user is None:
            raise RuntimeError(f"Seed user {user_email} was not created.")
        watchlist = database.scalar(select(Watchlist).where(Watchlist.user_id == user.id))
        if watchlist is None:
            raise RuntimeError(f"Seed watchlist for {user_email} was not created.")
        item = database.scalar(
            select(WatchlistItem).where(
                WatchlistItem.watchlist_id == watchlist.id,
                WatchlistItem.symbol == symbol,
            )
        )
        if item is None:
            database.add(WatchlistItem(watchlist_id=watchlist.id, symbol=symbol))
            database.commit()


def main() -> None:
    ensure_user("admin@stockai.local", "StockAI Administrator", UserRole.ADMIN)
    ensure_user("user@stockai.local", "Demo Investor", UserRole.USER)
    ensure_user("maya@stockai.local", "Maya Chen", UserRole.USER)

    ensure_opening_position("user@stockai.local", "AAPL", "12", "184.25")
    ensure_opening_position("user@stockai.local", "NVDA", "8", "137.80")
    ensure_opening_position("maya@stockai.local", "MSFT", "5", "412.10")
    ensure_opening_position("maya@stockai.local", "TSLA", "3", "298.40")
    ensure_watchlist_item("user@stockai.local", "MSFT")
    ensure_watchlist_item("user@stockai.local", "TSLA")

    print("Demo users seeded.")
    print("Admin: admin@stockai.local / StockAI123!")
    print("User:  user@stockai.local / StockAI123!")


if __name__ == "__main__":
    main()
