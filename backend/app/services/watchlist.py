from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.models.user import User
from app.models.watchlist import Watchlist, WatchlistItem
from app.schemas.watchlist import WatchlistItemResponse, WatchlistResponse


def _watchlist_response(watchlist: Watchlist) -> WatchlistResponse:
    return WatchlistResponse(
        id=watchlist.id,
        name=watchlist.name,
        items=[
            WatchlistItemResponse(id=item.id, symbol=item.symbol, added_at=item.added_at)
            for item in watchlist.items
        ],
    )


def get_default_watchlist(database: Session, user_id: UUID) -> Watchlist:
    watchlist = database.scalar(
        select(Watchlist)
        .options(selectinload(Watchlist.items))
        .execution_options(populate_existing=True)
        .where(Watchlist.user_id == user_id)
        .order_by(Watchlist.created_at)
    )
    if watchlist is None:
        watchlist = Watchlist(user_id=user_id, name="My Watchlist")
        database.add(watchlist)
        database.commit()
        database.refresh(watchlist)
    return watchlist


def get_user_watchlist(database: Session, user: User) -> WatchlistResponse:
    return _watchlist_response(get_default_watchlist(database, user.id))


def add_watchlist_item(database: Session, user: User, symbol: str) -> WatchlistResponse:
    watchlist = get_default_watchlist(database, user.id)
    normalized_symbol = symbol.strip().upper()
    item = database.scalar(
        select(WatchlistItem).where(
            WatchlistItem.watchlist_id == watchlist.id,
            WatchlistItem.symbol == normalized_symbol,
        )
    )
    if item is None:
        database.add(WatchlistItem(watchlist_id=watchlist.id, symbol=normalized_symbol))
        database.commit()
    return _watchlist_response(get_default_watchlist(database, user.id))


def remove_watchlist_item(database: Session, user: User, symbol: str) -> WatchlistResponse:
    watchlist = get_default_watchlist(database, user.id)
    database.execute(
        delete(WatchlistItem).where(
            WatchlistItem.watchlist_id == watchlist.id,
            WatchlistItem.symbol == symbol.strip().upper(),
        )
    )
    database.commit()
    return _watchlist_response(get_default_watchlist(database, user.id))
