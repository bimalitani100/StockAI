from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class WatchlistItemResponse(BaseModel):
    id: UUID
    symbol: str
    added_at: datetime


class WatchlistResponse(BaseModel):
    id: UUID
    name: str
    items: list[WatchlistItemResponse]
