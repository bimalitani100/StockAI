from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.providers.market import (
    MarketDataProvider,
    MarketDataUnavailableError,
    SymbolNotFoundError,
)
from app.providers.yahoo_finance import yahoo_finance_provider
from app.schemas.market import MarketHistory, MarketRange, MarketSummary
from app.services.market import get_market_history, get_market_summary

router = APIRouter()


def get_market_data_provider() -> MarketDataProvider:
    return yahoo_finance_provider


@router.get("/market-summary", response_model=MarketSummary)
def market_summary(
    symbol: Annotated[
        str,
        Query(
            min_length=1,
            max_length=10,
            pattern=r"^[A-Za-z][A-Za-z0-9.-]*$",
            description="Exchange ticker symbol, such as AAPL or BRK.B",
        ),
    ] = "NVDA",
    provider: MarketDataProvider = Depends(get_market_data_provider),
) -> MarketSummary:
    """Return a current quote summary for a ticker symbol."""
    try:
        return get_market_summary(symbol, provider)
    except SymbolNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except MarketDataUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error


@router.get("/market-history", response_model=MarketHistory)
def market_history(
    symbol: Annotated[
        str,
        Query(
            min_length=1,
            max_length=10,
            pattern=r"^[A-Za-z][A-Za-z0-9.-]*$",
            description="Exchange ticker symbol, such as AAPL or BRK.B",
        ),
    ] = "NVDA",
    time_range: Annotated[
        MarketRange,
        Query(alias="range", description="Chart window"),
    ] = "1d",
    provider: MarketDataProvider = Depends(get_market_data_provider),
) -> MarketHistory:
    """Return chart-ready historical prices for a ticker symbol."""
    try:
        return get_market_history(symbol, time_range, provider)
    except SymbolNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except MarketDataUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error
