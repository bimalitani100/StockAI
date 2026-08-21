from datetime import datetime
from typing import Literal

from pydantic import BaseModel


MarketRange = Literal["1d", "1w", "1m", "3m", "ytd", "1y", "5y", "max"]


class MarketSummary(BaseModel):
    """Public response contract for a market summary."""

    symbol: str
    company_name: str
    price: float
    currency: str
    previous_close: float
    change: float
    change_percent: float
    market_state: str
    as_of: datetime
    source: str
    is_realtime: bool
    refresh_seconds: int


class MarketHistoryPoint(BaseModel):
    timestamp: datetime
    price: float


class MarketHistory(BaseModel):
    """Historical prices shaped for an interactive research chart."""

    symbol: str
    company_name: str
    currency: str
    range: MarketRange
    interval: str
    price: float
    baseline_price: float
    change: float
    change_percent: float
    market_state: str
    as_of: datetime
    points: list[MarketHistoryPoint]
    source: str
    is_realtime: bool
    refresh_seconds: int
