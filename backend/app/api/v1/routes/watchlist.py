from typing import Annotated

from fastapi import APIRouter, Path

from app.api.dependencies import CurrentUser, DatabaseSession
from app.schemas.watchlist import WatchlistResponse
from app.services.watchlist import add_watchlist_item, get_user_watchlist, remove_watchlist_item

router = APIRouter()
TickerSymbol = Annotated[str, Path(min_length=1, max_length=10, pattern=r"^[A-Za-z][A-Za-z0-9.-]*$")]


@router.get("", response_model=WatchlistResponse)
def watchlist(current_user: CurrentUser, database: DatabaseSession) -> WatchlistResponse:
    return get_user_watchlist(database, current_user)


@router.put("/items/{symbol}", response_model=WatchlistResponse)
def add_item(
    symbol: TickerSymbol,
    current_user: CurrentUser,
    database: DatabaseSession,
) -> WatchlistResponse:
    return add_watchlist_item(database, current_user, symbol)


@router.delete("/items/{symbol}", response_model=WatchlistResponse)
def remove_item(
    symbol: TickerSymbol,
    current_user: CurrentUser,
    database: DatabaseSession,
) -> WatchlistResponse:
    return remove_watchlist_item(database, current_user, symbol)
