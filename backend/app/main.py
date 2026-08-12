from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


class MarketSummary(BaseModel):
    """Public response contract for the first frontend-to-backend request."""

    symbol: str
    company_name: str
    price: float
    currency: str
    change_percent: float
    as_of: datetime
    source: str


app = FastAPI(
    title="StockAI API",
    version="0.1.0",
    description="Backend service for the StockAI research platform.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/market-summary", response_model=MarketSummary, tags=["market"])
def get_market_summary() -> MarketSummary:
    """Return deterministic demo data until a market-data provider is selected."""
    return MarketSummary(
        symbol="NVDA",
        company_name="NVIDIA Corporation",
        price=184.91,
        currency="USD",
        change_percent=1.76,
        as_of=datetime(2026, 8, 11, 20, 0, tzinfo=UTC),
        source="StockAI demo dataset",
    )
