"use client";

import { type FormEvent, useCallback, useEffect, useRef, useState } from "react";

import { MarketPriceChart } from "@/components/market/market-price-chart";
import { fetchMarketHistory, fetchMarketSummary } from "@/lib/api";
import type { MarketHistory, MarketRange, MarketSummary } from "@/types/market";

type SummaryState =
  | { status: "loading" }
  | { status: "success"; summary: MarketSummary }
  | { status: "error"; message: string };

type SearchRequest = { symbol: string; requestId: number };
type PriceMovement = "up" | "down" | null;

const RANGE_OPTIONS: Array<{ value: MarketRange; label: string }> = [
  { value: "1d", label: "1D" },
  { value: "1w", label: "1W" },
  { value: "1m", label: "1M" },
  { value: "3m", label: "3M" },
  { value: "ytd", label: "YTD" },
  { value: "1y", label: "1Y" },
  { value: "5y", label: "5Y" },
  { value: "max", label: "MAX" },
];

function normalizeSymbol(value: string): string {
  const normalized = value.trim().toUpperCase();
  return /^[A-Z][A-Z0-9.-]{0,9}$/.test(normalized) ? normalized : "NVDA";
}

function money(value: number, currency: string): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(value);
}

function marketStateLabel(state: string): string {
  if (state === "pre") return "Pre-market";
  if (state === "regular") return "Market open";
  if (state === "post") return "After-hours";
  return "Market closed";
}

export function MarketSummaryCard({ initialSymbol = "NVDA" }: { initialSymbol?: string }) {
  const normalizedInitialSymbol = normalizeSymbol(initialSymbol);
  const [symbolInput, setSymbolInput] = useState(normalizedInitialSymbol);
  const [search, setSearch] = useState<SearchRequest>({ symbol: normalizedInitialSymbol, requestId: 0 });
  const [summaryState, setSummaryState] = useState<SummaryState>({ status: "loading" });
  const [history, setHistory] = useState<MarketHistory | null>(null);
  const [chartRange, setChartRange] = useState<MarketRange>("1d");
  const [chartLoading, setChartLoading] = useState(true);
  const [chartError, setChartError] = useState<string | null>(null);
  const [autoRefreshError, setAutoRefreshError] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [priceMovement, setPriceMovement] = useState<PriceMovement>(null);
  const lastPrice = useRef<number | null>(null);
  const movementTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const applySummary = useCallback((summary: MarketSummary) => {
    const previousPrice = lastPrice.current;
    if (previousPrice !== null && summary.price !== previousPrice) {
      setPriceMovement(summary.price > previousPrice ? "up" : "down");
      if (movementTimer.current) clearTimeout(movementTimer.current);
      movementTimer.current = setTimeout(() => setPriceMovement(null), 900);
    }
    lastPrice.current = summary.price;
    setSummaryState({ status: "success", summary });
  }, []);

  useEffect(() => () => {
    if (movementTimer.current) clearTimeout(movementTimer.current);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    lastPrice.current = null;

    fetchMarketSummary(search.symbol, controller.signal)
      .then(applySummary)
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setSummaryState({
          status: "error",
          message: error instanceof Error ? error.message : "Unexpected API error",
        });
      });

    return () => controller.abort();
  }, [applySummary, search]);

  useEffect(() => {
    const controller = new AbortController();

    fetchMarketHistory(search.symbol, chartRange, controller.signal)
      .then(setHistory)
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setChartError(error instanceof Error ? error.message : "Unable to load chart history.");
      })
      .finally(() => {
        if (!controller.signal.aborted) setChartLoading(false);
      });

    return () => controller.abort();
  }, [chartRange, search]);

  useEffect(() => {
    let activeController: AbortController | null = null;
    const interval = window.setInterval(async () => {
      if (document.visibilityState !== "visible") return;
      activeController?.abort();
      const controller = new AbortController();
      activeController = controller;
      setIsRefreshing(true);
      try {
        const summary = await fetchMarketSummary(search.symbol, controller.signal);
        applySummary(summary);
        setAutoRefreshError(null);
      } catch (error) {
        if (!controller.signal.aborted) {
          setAutoRefreshError(error instanceof Error ? error.message : "Automatic update delayed.");
        }
      } finally {
        if (!controller.signal.aborted) setIsRefreshing(false);
      }
    }, 15_000);

    return () => {
      window.clearInterval(interval);
      activeController?.abort();
    };
  }, [applySummary, search]);

  useEffect(() => {
    if (chartRange !== "1d") return;
    let activeController: AbortController | null = null;
    const interval = window.setInterval(async () => {
      if (document.visibilityState !== "visible") return;
      activeController?.abort();
      const controller = new AbortController();
      activeController = controller;
      try {
        setHistory(await fetchMarketHistory(search.symbol, "1d", controller.signal));
        setChartError(null);
      } catch (error) {
        if (!controller.signal.aborted) {
          setChartError(error instanceof Error ? error.message : "Chart update delayed.");
        }
      }
    }, 60_000);

    return () => {
      window.clearInterval(interval);
      activeController?.abort();
    };
  }, [chartRange, search]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedSymbol = symbolInput.trim().toUpperCase();
    if (/^[A-Z][A-Z0-9.-]{0,9}$/.test(normalizedSymbol)) {
      setSummaryState({ status: "loading" });
      setHistory(null);
      setChartLoading(true);
      setChartError(null);
      setAutoRefreshError(null);
      setChartRange("1d");
      setSearch((current) => ({ symbol: normalizedSymbol, requestId: current.requestId + 1 }));
    }
  }

  const summary = summaryState.status === "success" ? summaryState.summary : null;
  const activeHistory = history?.range === chartRange && history.symbol === search.symbol ? history : null;
  const displayedChange = activeHistory?.change ?? summary?.change ?? 0;
  const displayedChangePercent = activeHistory?.change_percent ?? summary?.change_percent ?? 0;
  const isPositive = displayedChange >= 0;
  const selectedRangeLabel = RANGE_OPTIONS.find((option) => option.value === chartRange)?.label ?? "1D";

  return (
    <>
      <div className="section-heading">
        <div>
          <span className="kicker">AUTO-UPDATING MARKET RESEARCH</span>
          <h2 id="workspace-title">Search a stock</h2>
        </div>
        <span className={`status ${summary ? "online" : ""}`}>
          <i /> {summary ? (isRefreshing ? "Updating price…" : "Auto-refresh on") : "Waiting for API"}
        </span>
      </div>

      <form className="symbol-search" onSubmit={handleSubmit}>
        <label htmlFor="symbol">Ticker symbol</label>
        <div className="search-controls">
          <input
            id="symbol"
            name="symbol"
            value={symbolInput}
            onChange={(event) => setSymbolInput(event.target.value)}
            placeholder="AAPL"
            maxLength={10}
            autoComplete="off"
            spellCheck={false}
          />
          <button type="submit" disabled={summaryState.status === "loading"}>
            {summaryState.status === "loading" ? "Loading…" : "Open chart"}
          </button>
        </div>
        <p>Try AAPL, MSFT, TSLA, AMZN, or BRK.B</p>
      </form>

      <article className="quote-card live-quote-card" aria-live="polite">
        {summary ? (
          <>
            <div className="live-quote-heading">
              <div>
                <span className="quote-symbol">{summary.symbol}</span>
                <h3>{summary.company_name}</h3>
                <div className={`live-price price-${priceMovement ?? "steady"}`}>
                  {money(summary.price, summary.currency)}
                </div>
                <div className={`range-change ${isPositive ? "positive" : "negative"}`}>
                  {isPositive ? "+" : ""}{money(displayedChange, summary.currency)} ({isPositive ? "+" : ""}{displayedChangePercent.toFixed(2)}%)
                  <span>{selectedRangeLabel}</span>
                </div>
              </div>
              <div className="quote-freshness">
                <span className={`market-state state-${summary.market_state}`}>{marketStateLabel(summary.market_state)}</span>
                <strong>{summary.is_realtime ? "Live stream" : `Auto ${summary.refresh_seconds}s`}</strong>
                <time>{new Date(summary.as_of).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", second: "2-digit" })}</time>
              </div>
            </div>

            {autoRefreshError && <p className="feed-warning">Latest automatic update failed; the last good price remains visible. Retrying automatically.</p>}
            {chartError && <p className="feed-warning">{chartError}</p>}

            <div className={`chart-stage ${chartLoading ? "is-loading" : ""}`}>
              {activeHistory ? <MarketPriceChart history={activeHistory} /> : <div className="chart-loading">Loading {selectedRangeLabel} price history…</div>}
            </div>

            <div className="range-picker" aria-label="Chart time range">
              {RANGE_OPTIONS.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  className={chartRange === option.value ? "active" : ""}
                  onClick={() => {
                    if (chartRange === option.value) return;
                    setChartLoading(true);
                    setChartError(null);
                    setChartRange(option.value);
                  }}
                  aria-pressed={chartRange === option.value}
                >
                  {option.label}
                </button>
              ))}
            </div>

            <div className="quote-footer">
              <span>{summary.source}</span>
              <span>{summary.is_realtime ? "Streaming market data" : "Polling automatically · not exchange-grade real-time"}</span>
            </div>
          </>
        ) : (
          <div className="empty-state">
            <div className="pulse" />
            <div>
              <strong>
                {summaryState.status === "error"
                  ? summaryState.message
                  : `Requesting ${search.symbol} market data…`}
              </strong>
              <p>Check the symbol or confirm FastAPI is running on port 8000.</p>
            </div>
          </div>
        )}
      </article>
    </>
  );
}
