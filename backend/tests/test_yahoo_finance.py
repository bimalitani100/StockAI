import io
import json
from datetime import UTC, datetime

import pytest

import app.providers.yahoo_finance as yahoo_finance_module
from app.providers.market import SymbolNotFoundError
from app.providers.yahoo_finance import YahooFinanceProvider


def response_for(payload: dict) -> io.BytesIO:
    return io.BytesIO(json.dumps(payload).encode())


def test_provider_maps_yahoo_metadata_to_public_contract(monkeypatch) -> None:
    payload = {
        "chart": {
            "result": [
                {
                    "meta": {
                        "symbol": "AAPL",
                        "longName": "Apple Inc.",
                        "regularMarketPrice": 230.12,
                        "previousClose": 228.0,
                        "currency": "USD",
                        "regularMarketTime": 1787148000,
                    },
                    "timestamp": [1787147940, 1787148000],
                    "indicators": {"quote": [{"close": [229.9, 230.12]}]},
                }
            ],
            "error": None,
        }
    }
    monkeypatch.setattr(
        yahoo_finance_module,
        "urlopen",
        lambda request, timeout: response_for(payload),
    )

    summary = YahooFinanceProvider().get_summary("AAPL")

    assert summary.symbol == "AAPL"
    assert summary.company_name == "Apple Inc."
    assert summary.price == 230.12
    assert summary.previous_close == 228.0
    assert summary.change == 2.12
    assert summary.change_percent == 0.93
    assert summary.is_realtime is False


def test_provider_maps_chart_points_and_range_change(monkeypatch) -> None:
    payload = {
        "chart": {
            "result": [
                {
                    "meta": {
                        "symbol": "NVDA",
                        "longName": "NVIDIA Corporation",
                        "chartPreviousClose": 210.0,
                        "currency": "USD",
                    },
                    "timestamp": [1787147940, 1787148000, 1787148060],
                    "indicators": {"quote": [{"close": [211.0, None, 214.2]}]},
                }
            ],
            "error": None,
        }
    }
    monkeypatch.setattr(
        yahoo_finance_module,
        "urlopen",
        lambda request, timeout: response_for(payload),
    )

    history = YahooFinanceProvider().get_history("NVDA", "1d")

    assert history.symbol == "NVDA"
    assert history.interval == "1m"
    assert history.baseline_price == 210.0
    assert history.price == 214.2
    assert history.change == 4.2
    assert [point.price for point in history.points] == [211.0, 214.2]
    assert history.points[1].timestamp == datetime.fromtimestamp(1787148060, tz=UTC)


def test_provider_reports_unknown_symbol(monkeypatch) -> None:
    payload = {"chart": {"result": None, "error": {"code": "Not Found"}}}
    monkeypatch.setattr(
        yahoo_finance_module,
        "urlopen",
        lambda request, timeout: response_for(payload),
    )

    with pytest.raises(SymbolNotFoundError):
        YahooFinanceProvider().get_summary("NOPE")
