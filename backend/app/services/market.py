from app.providers.market import MarketDataProvider
from app.schemas.market import MarketHistory, MarketRange, MarketSummary


def get_market_summary(symbol: str, provider: MarketDataProvider) -> MarketSummary:
    """Normalize input before crossing the external-provider boundary."""
    return provider.get_summary(symbol.strip().upper())


def get_market_history(
    symbol: str,
    time_range: MarketRange,
    provider: MarketDataProvider,
) -> MarketHistory:
    """Normalize chart input before crossing the provider boundary."""
    return provider.get_history(symbol.strip().upper(), time_range)
