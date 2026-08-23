import json
from datetime import UTC, datetime
from numbers import Real
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from app.providers.market import (
    MarketDataProvider,
    MarketDataUnavailableError,
    SymbolNotFoundError,
)
from app.schemas.market import (
    MarketHistory,
    MarketHistoryPoint,
    MarketRange,
    MarketSummary,
)


class YahooFinanceProvider(MarketDataProvider):
    """Development adapter backed by Yahoo's unofficial chart endpoint."""

    base_url = "https://query1.finance.yahoo.com/v8/finance/chart"
    source_name = "Yahoo Finance (development source; may be delayed)"
    refresh_seconds = 15
    range_configuration: dict[MarketRange, tuple[str, str]] = {
        "1d": ("1d", "1m"),
        "1w": ("5d", "15m"),
        "1m": ("1mo", "1h"),
        "3m": ("3mo", "1d"),
        "ytd": ("ytd", "1d"),
        "1y": ("1y", "1d"),
        "5y": ("5y", "1wk"),
        "max": ("max", "1mo"),
    }

    def get_summary(self, symbol: str) -> MarketSummary:
        result = self._get_chart(symbol, provider_range="1d", interval="1m")
        metadata = result.get("meta") or {}
        timestamps, prices = self._price_series(result)
        metadata_price = self._number(metadata.get("regularMarketPrice"))
        price = prices[-1] if prices else metadata_price
        if price is None:
            raise SymbolNotFoundError(f"No market data was found for {symbol}.")

        previous_close = self._number(
            metadata.get("chartPreviousClose") or metadata.get("previousClose")
        )
        if previous_close is None:
            previous_close = price

        change = price - previous_close
        change_percent = (change / previous_close) * 100 if previous_close else 0.0
        as_of = self._as_of(metadata, timestamps)

        return MarketSummary(
            symbol=str(metadata.get("symbol") or symbol).upper(),
            company_name=self._company_name(metadata, symbol),
            price=round(price, 2),
            currency=str(metadata.get("currency") or "USD"),
            previous_close=round(previous_close, 2),
            change=round(change, 2),
            change_percent=round(change_percent, 2),
            market_state=self._market_state(metadata),
            as_of=as_of,
            source=self.source_name,
            is_realtime=False,
            refresh_seconds=self.refresh_seconds,
        )

    def get_history(self, symbol: str, time_range: MarketRange) -> MarketHistory:
        provider_range, interval = self.range_configuration[time_range]
        result = self._get_chart(symbol, provider_range=provider_range, interval=interval)
        metadata = result.get("meta") or {}
        timestamps, prices = self._price_series(result)
        if not prices:
            raise SymbolNotFoundError(f"No chart data was found for {symbol}.")

        points = [
            MarketHistoryPoint(
                timestamp=datetime.fromtimestamp(timestamp, tz=UTC),
                price=round(price, 4),
            )
            for timestamp, price in zip(timestamps, prices, strict=True)
        ]
        latest_price = prices[-1]
        previous_close = self._number(
            metadata.get("chartPreviousClose") or metadata.get("previousClose")
        )
        baseline_price = previous_close if time_range == "1d" and previous_close else prices[0]
        change = latest_price - baseline_price
        change_percent = (change / baseline_price) * 100 if baseline_price else 0.0

        return MarketHistory(
            symbol=str(metadata.get("symbol") or symbol).upper(),
            company_name=self._company_name(metadata, symbol),
            currency=str(metadata.get("currency") or "USD"),
            range=time_range,
            interval=interval,
            price=round(latest_price, 2),
            baseline_price=round(baseline_price, 2),
            change=round(change, 2),
            change_percent=round(change_percent, 2),
            market_state=self._market_state(metadata),
            as_of=points[-1].timestamp,
            points=points,
            source=self.source_name,
            is_realtime=False,
            refresh_seconds=self.refresh_seconds,
        )

    def _get_chart(self, symbol: str, *, provider_range: str, interval: str) -> dict[str, Any]:
        query = urlencode(
            {
                "interval": interval,
                "range": provider_range,
                "includePrePost": "true",
                "events": "div,splits",
            }
        )
        url = f"{self.base_url}/{quote(symbol, safe='')}?{query}"
        request = Request(url, headers={"User-Agent": "Mozilla/5.0 StockAI/0.7"})

        try:
            with urlopen(request, timeout=8) as response:
                payload: dict[str, Any] = json.load(response)
        except HTTPError as error:
            if error.code == 404:
                raise SymbolNotFoundError(f"No market data was found for {symbol}.") from error
            raise MarketDataUnavailableError("The market-data provider did not respond.") from error
        except (URLError, TimeoutError, json.JSONDecodeError) as error:
            raise MarketDataUnavailableError("The market-data provider did not respond.") from error

        chart = payload.get("chart") or {}
        results = chart.get("result") or []
        if chart.get("error") or not results:
            raise SymbolNotFoundError(f"No market data was found for {symbol}.")
        return results[0]

    def _price_series(self, result: dict[str, Any]) -> tuple[list[int], list[float]]:
        raw_timestamps = result.get("timestamp") or []
        indicators = result.get("indicators") or {}
        quotes = indicators.get("quote") or []
        raw_closes = (quotes[0].get("close") or []) if quotes else []

        timestamps: list[int] = []
        prices: list[float] = []
        for timestamp, raw_price in zip(raw_timestamps, raw_closes):
            price = self._number(raw_price)
            if isinstance(timestamp, int) and price is not None:
                timestamps.append(timestamp)
                prices.append(price)
        return timestamps, prices

    @staticmethod
    def _company_name(metadata: dict[str, Any], symbol: str) -> str:
        return str(metadata.get("longName") or metadata.get("shortName") or symbol)

    def _as_of(self, metadata: dict[str, Any], timestamps: list[int]) -> datetime:
        if timestamps:
            return datetime.fromtimestamp(timestamps[-1], tz=UTC)
        market_time = self._number(metadata.get("regularMarketTime"))
        return (
            datetime.fromtimestamp(market_time, tz=UTC)
            if market_time is not None
            else datetime.now(UTC)
        )

    @staticmethod
    def _market_state(metadata: dict[str, Any]) -> str:
        now = datetime.now(UTC).timestamp()
        periods = metadata.get("currentTradingPeriod") or {}
        for name in ("pre", "regular", "post"):
            period = periods.get(name) or {}
            start = period.get("start")
            end = period.get("end")
            if isinstance(start, int) and isinstance(end, int) and start <= now < end:
                return name
        return "closed"

    @staticmethod
    def _number(value: object) -> float | None:
        if isinstance(value, Real) and not isinstance(value, bool):
            return float(value)
        return None


yahoo_finance_provider = YahooFinanceProvider()
