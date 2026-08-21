from typing import Protocol

from app.schemas.market import MarketHistory, MarketRange, MarketSummary


class MarketDataError(Exception):
    """Base error for failures at the external market-data boundary."""


class SymbolNotFoundError(MarketDataError):
    """Raised when a provider cannot find a requested symbol."""


class MarketDataUnavailableError(MarketDataError):
    """Raised when a provider cannot currently serve a valid response."""


class MarketDataProvider(Protocol):
    def get_summary(self, symbol: str) -> MarketSummary:
        """Return a current summary for a normalized ticker symbol."""
        ...

    def get_history(self, symbol: str, time_range: MarketRange) -> MarketHistory:
        """Return chart-ready price history for a normalized ticker symbol."""
        ...
