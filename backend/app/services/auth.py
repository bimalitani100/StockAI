from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.portfolio import Portfolio
from app.models.user import User, UserRole
from app.models.watchlist import Watchlist
from app.schemas.auth import PasswordChangeRequest, ProfileUpdateRequest, RegisterRequest


class CurrentPasswordIncorrectError(ValueError):
    pass


class PasswordUnchangedError(ValueError):
    pass


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


def update_profile(database: Session, user: User, request: ProfileUpdateRequest) -> User:
    user.full_name = request.full_name
    database.commit()
    database.refresh(user)
    return user


def change_password(database: Session, user: User, request: PasswordChangeRequest) -> None:
    if not verify_password(request.current_password, user.password_hash):
        raise CurrentPasswordIncorrectError("Current password is incorrect.")
    if verify_password(request.new_password, user.password_hash):
        raise PasswordUnchangedError("The new password must be different from the current password.")
    user.password_hash = hash_password(request.new_password)
    database.commit()
