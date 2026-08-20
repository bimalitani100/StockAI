from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.portfolio import Portfolio
from app.models.user import User, UserRole
from app.models.watchlist import Watchlist
from app.schemas.auth import RegisterRequest


def get_user_by_email(database: Session, email: str) -> User | None:
    return database.scalar(select(User).where(User.email == email.strip().lower()))


def register_user(database: Session, request: RegisterRequest) -> User:
    user = User(
        full_name=request.full_name,
        email=request.email,
        password_hash=hash_password(request.password),
        role=UserRole.USER,
    )
    user.portfolios.append(Portfolio(name="Primary Portfolio"))
    user.watchlists.append(Watchlist(name="My Watchlist"))
    database.add(user)
    database.commit()
    database.refresh(user)
    return user


def authenticate_user(database: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(database, email)
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        return None
    return user
