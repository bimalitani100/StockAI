"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useEffect, useState } from "react";

import {
  addToWatchlist,
  getAccounting,
  getCashEvents,
  getPortfolio,
  getPortfolioValuation,
  getSession,
  getTransactions,
  getWatchlist,
  logout,
  recordCashEvent,
  recordTransaction,
  removeFromWatchlist,
} from "@/lib/auth-api";
import { ApiRequestError } from "@/lib/api";
import type { AuthUser } from "@/types/auth";
import type {
  AccountingSummary,
  CashEvent,
  CashEventType,
  Portfolio,
  PortfolioTransaction,
  PortfolioValuation,
  TransactionType,
  Watchlist,
} from "@/types/portfolio";

function localDateTimeValue(): string {
  const now = new Date();
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
  return now.toISOString().slice(0, 16);
}

function money(value: number): string {
  return value.toLocaleString(undefined, { style: "currency", currency: "USD" });
}

function transactionLabel(type: TransactionType): string {
  if (type === "opening_balance") return "Opening";
  return type === "buy" ? "Buy" : "Sell";
}

function cashEventLabel(type: CashEventType): string {
  return type.replace("_", " ");
}

export function UserDashboard() {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [transactions, setTransactions] = useState<PortfolioTransaction[] | null>(null);
  const [watchlist, setWatchlist] = useState<Watchlist | null>(null);
  const [accounting, setAccounting] = useState<AccountingSummary | null>(null);
  const [cashEvents, setCashEvents] = useState<CashEvent[] | null>(null);
  const [valuation, setValuation] = useState<PortfolioValuation | null>(null);
  const [valuationLoading, setValuationLoading] = useState(true);
  const [valuationError, setValuationError] = useState<string | null>(null);

  const [transactionType, setTransactionType] = useState<"buy" | "sell">("buy");
  const [symbol, setSymbol] = useState("");
  const [quantity, setQuantity] = useState("");
  const [price, setPrice] = useState("");
  const [fee, setFee] = useState("0");
  const [occurredAt, setOccurredAt] = useState(localDateTimeValue);

  const [cashEventType, setCashEventType] = useState<"deposit" | "withdrawal" | "dividend">("deposit");
  const [cashAmount, setCashAmount] = useState("");
  const [cashSymbol, setCashSymbol] = useState("");
  const [cashOccurredAt, setCashOccurredAt] = useState(localDateTimeValue);
  const [watchSymbol, setWatchSymbol] = useState("");

  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    Promise.all([
      getSession(),
      getPortfolio(),
      getTransactions(),
      getWatchlist(),
      getAccounting(),
      getCashEvents(),
    ])
      .then(([session, loadedPortfolio, loadedTransactions, loadedWatchlist, loadedAccounting, loadedCashEvents]) => {
        if (session.user.role === "admin") {
          router.replace("/admin");
          return;
        }
        setUser(session.user);
        setPortfolio(loadedPortfolio);
        setTransactions(loadedTransactions);
        setWatchlist(loadedWatchlist);
        setAccounting(loadedAccounting);
        setCashEvents(loadedCashEvents);
      })
      .catch((requestError: unknown) => {
        if (requestError instanceof ApiRequestError && requestError.status === 401) {
          router.replace("/login");
          return;
        }
        setError(requestError instanceof Error ? requestError.message : "Unable to load dashboard.");
      });

    getPortfolioValuation()
      .then(setValuation)
      .catch((requestError: unknown) => {
        setValuationError(requestError instanceof Error ? requestError.message : "Unable to value portfolio.");
      })
      .finally(() => setValuationLoading(false));
  }, [router]);

  async function refreshValuation() {
    setValuationLoading(true);
    setValuationError(null);
    try {
      setValuation(await getPortfolioValuation());
    } catch (requestError) {
      setValuationError(requestError instanceof Error ? requestError.message : "Unable to value portfolio.");
    } finally {
      setValuationLoading(false);
    }
  }

  async function handleTransactionSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const result = await recordTransaction(
        transactionType,
        symbol.trim().toUpperCase(),
        Number(quantity),
        Number(price),
        Number(fee),
        new Date(occurredAt).toISOString(),
      );
      setPortfolio(result.portfolio);
      setAccounting(result.accounting);
      setTransactions(await getTransactions());
      setNotice(`${transactionType === "buy" ? "Buy" : "Sell"} recorded for ${result.transaction.symbol}.`);
      setSymbol("");
      setQuantity("");
      setPrice("");
      setFee("0");
      await refreshValuation();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to record transaction.");
    } finally {
      setSaving(false);
    }
  }

  async function handleCashEventSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const result = await recordCashEvent(
        cashEventType,
        Number(cashAmount),
        new Date(cashOccurredAt).toISOString(),
        cashEventType === "dividend" ? cashSymbol.trim().toUpperCase() : undefined,
      );
      setAccounting(result.accounting);
      setCashEvents(await getCashEvents());
      setNotice(`${cashEventLabel(result.cash_event.event_type)} recorded.`);
      setCashAmount("");
      setCashSymbol("");
      await refreshValuation();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to record cash activity.");
    } finally {
      setSaving(false);
    }
  }

  async function handleWatchlistSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      setWatchlist(await addToWatchlist(watchSymbol.trim().toUpperCase()));
      setWatchSymbol("");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to update watchlist.");
    }
  }

  async function handleWatchlistRemove(symbolToRemove: string) {
    setError(null);
    try {
      setWatchlist(await removeFromWatchlist(symbolToRemove));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to update watchlist.");
    }
  }

  async function handleLogout() {
    await logout();
    router.replace("/login");
    router.refresh();
  }

  if (!user || !portfolio || !transactions || !watchlist || !accounting || !cashEvents) {
    return <main className="portal-loading">{error ?? "Loading your StockAI workspace…"}</main>;
  }

  const totalValue = valuation?.is_complete && valuation.total_value !== null
    ? money(valuation.total_value)
    : "Pending quotes";
  const totalReturn = valuation?.is_complete && valuation.total_return !== null
    ? money(valuation.total_return)
    : "—";

  return (
    <main className="portal-shell">
      <aside className="portal-sidebar">
        <Link className="portal-brand" href="/dashboard">StockAI <small>v0.6</small></Link>
        <nav>
          <a className="active" href="#overview">Performance</a>
          <a href="#cash">Cash</a>
          <a href="#transactions">Transactions</a>
          <a href="#holdings">Holdings</a>
          <a href="#watchlist">Watchlist</a>
          <Link href="/market">Market search</Link>
        </nav>
        <button className="text-action" onClick={handleLogout}>Sign out</button>
      </aside>

      <section className="portal-content">
        <header className="portal-header" id="overview">
          <div><span className="kicker">ACCOUNTING WORKSPACE</span><h1>Good to see you, {user.full_name.split(" ")[0]}.</h1></div>
          <span className="role-badge">User</span>
        </header>

        {error && <p className="portal-error" role="alert">{error}</p>}
        {notice && <p className="portal-notice" role="status">{notice}</p>}

        <section className="metric-grid performance-grid">
          <article><span>Total value</span><strong>{totalValue}</strong></article>
          <article><span>Available cash</span><strong>{money(accounting.cash_balance)}</strong></article>
          <article><span>Total return</span><strong>{totalReturn}</strong></article>
          <article><span>Return rate</span><strong>{valuation?.total_return_percent === null || valuation?.total_return_percent === undefined ? "—" : `${valuation.total_return_percent.toFixed(2)}%`}</strong></article>
        </section>

        <section className="portal-panel performance-panel">
          <div className="panel-heading">
            <div><span className="kicker">LIVE VALUATION</span><h2>Portfolio performance</h2><p>Market value minus net contributions; quotes are development data.</p></div>
            <button className="table-action" type="button" onClick={refreshValuation} disabled={valuationLoading}>{valuationLoading ? "Refreshing…" : "Refresh quotes"}</button>
          </div>
          {valuationError && <p className="valuation-warning">{valuationError}</p>}
          {valuation && !valuation.is_complete && <p className="valuation-warning">A complete total is hidden because one or more holdings could not be valued safely.</p>}
          {valuation?.holdings.length ? (
            <div className="data-table-wrap"><table className="data-table"><thead><tr><th>Symbol</th><th>Quantity</th><th>Cost basis</th><th>Current price</th><th>Market value</th><th>Unrealized</th></tr></thead><tbody>
              {valuation.holdings.map((holding) => <tr key={holding.symbol}><td><Link className="ticker-link" href={`/market?symbol=${encodeURIComponent(holding.symbol)}`}>{holding.symbol}</Link>{holding.error && <small>{holding.error}</small>}</td><td>{holding.quantity.toLocaleString()}</td><td>{money(holding.cost_basis)}</td><td>{holding.current_price === null ? "—" : money(holding.current_price)}</td><td>{holding.market_value === null ? "—" : money(holding.market_value)}</td><td className={holding.unrealized_gain !== null && holding.unrealized_gain >= 0 ? "gain" : "loss"}>{holding.unrealized_gain === null ? "—" : money(holding.unrealized_gain)}</td></tr>)}
            </tbody></table></div>
          ) : <p className="panel-empty">Record a funded purchase to begin live valuation.</p>}
          <div className="accounting-strip">
            <div><span>Net contributions</span><strong>{money(accounting.net_contributions)}</strong></div>
            <div><span>Realized gain</span><strong>{money(accounting.realized_gain)}</strong></div>
            <div><span>Dividends</span><strong>{money(accounting.dividend_income)}</strong></div>
            <div><span>Trade fees</span><strong>{money(accounting.trade_fees)}</strong></div>
          </div>
        </section>

        <section className="portal-panel" id="cash">
          <div className="panel-heading"><div><span className="kicker">CASH LEDGER</span><h2>Record cash activity</h2><p>Deposit before buying; withdrawals cannot exceed available cash.</p></div></div>
          <form className="holding-form cash-form" onSubmit={handleCashEventSubmit}>
            <label>Activity<select value={cashEventType} onChange={(event) => setCashEventType(event.target.value as "deposit" | "withdrawal" | "dividend")}><option value="deposit">Deposit</option><option value="withdrawal">Withdrawal</option><option value="dividend">Dividend</option></select></label>
            <label>Amount<input type="number" min="0.01" step="0.01" value={cashAmount} onChange={(event) => setCashAmount(event.target.value)} required /></label>
            {cashEventType === "dividend" && <label>Symbol<input value={cashSymbol} onChange={(event) => setCashSymbol(event.target.value)} placeholder="AAPL" maxLength={10} required /></label>}
            <label>Date and time<input type="datetime-local" value={cashOccurredAt} onChange={(event) => setCashOccurredAt(event.target.value)} required /></label>
            <button className="primary-action" type="submit" disabled={saving}>{saving ? "Recording…" : "Record activity"}</button>
          </form>
          <div className="cash-event-list">
            {cashEvents.map((item) => <article key={item.id}><span>{cashEventLabel(item.event_type)}</span><strong>{money(item.amount)}</strong><small>{item.symbol ?? "Cash"}</small><time>{new Date(item.occurred_at).toLocaleDateString()}</time></article>)}
          </div>
        </section>

        <section className="portal-panel" id="transactions">
          <div className="panel-heading"><div><span className="kicker">TRADE LEDGER</span><h2>Record a transaction</h2><p>Buy fees join cost basis; sell fees reduce realized proceeds.</p></div></div>
          <form className="holding-form transaction-form" onSubmit={handleTransactionSubmit}>
            <label>Type<select value={transactionType} onChange={(event) => setTransactionType(event.target.value as "buy" | "sell")}><option value="buy">Buy</option><option value="sell">Sell</option></select></label>
            <label>Symbol<input value={symbol} onChange={(event) => setSymbol(event.target.value)} placeholder="AAPL" maxLength={10} required /></label>
            <label>Quantity<input type="number" min="0.000001" step="any" value={quantity} onChange={(event) => setQuantity(event.target.value)} required /></label>
            <label>Price per share<input type="number" min="0.0001" step="0.0001" value={price} onChange={(event) => setPrice(event.target.value)} required /></label>
            <label>Fee<input type="number" min="0" step="0.01" value={fee} onChange={(event) => setFee(event.target.value)} required /></label>
            <label>Date and time<input type="datetime-local" value={occurredAt} onChange={(event) => setOccurredAt(event.target.value)} required /></label>
            <button className="primary-action" type="submit" disabled={saving}>{saving ? "Recording…" : "Record transaction"}</button>
          </form>
        </section>

        <section className="portal-panel" id="holdings">
          <div className="panel-heading"><div><span className="kicker">CALCULATED SNAPSHOT</span><h2>Portfolio holdings</h2><p>Read-only positions derived from your transaction ledger.</p></div></div>
          {portfolio.holdings.length ? (
            <div className="data-table-wrap"><table className="data-table"><thead><tr><th>Symbol</th><th>Quantity</th><th>Average cost</th><th>Cost basis</th></tr></thead><tbody>
              {portfolio.holdings.map((holding) => <tr key={holding.id}><td><Link className="ticker-link" href={`/market?symbol=${encodeURIComponent(holding.symbol)}`}>{holding.symbol}</Link></td><td>{holding.quantity.toLocaleString()}</td><td>{money(holding.average_cost)}</td><td>{money(holding.total_cost)}</td></tr>)}
            </tbody></table></div>
          ) : <p className="panel-empty">No holdings yet. Deposit cash, then record your first buy.</p>}
        </section>

        <div className="portal-grid">
          <section className="portal-panel">
            <div className="panel-heading"><div><span className="kicker">LEDGER</span><h2>Recent trades</h2></div></div>
            {transactions.length ? <div className="transaction-list">{transactions.map((transaction) => <article key={transaction.id}><span className={`transaction-type ${transaction.transaction_type}`}>{transactionLabel(transaction.transaction_type)}</span><strong>{transaction.symbol}</strong><span>{transaction.quantity.toLocaleString()} × {money(transaction.price)}{transaction.fee ? ` + ${money(transaction.fee)} fee` : ""}</span><time>{new Date(transaction.occurred_at).toLocaleDateString()}</time></article>)}</div> : <p className="panel-empty">No transactions recorded yet.</p>}
          </section>

          <section className="portal-panel" id="watchlist">
            <div className="panel-heading"><div><span className="kicker">RESEARCH QUEUE</span><h2>{watchlist.name}</h2></div></div>
            <form className="watchlist-form" onSubmit={handleWatchlistSubmit}><input value={watchSymbol} onChange={(event) => setWatchSymbol(event.target.value)} placeholder="Add ticker" maxLength={10} required /><button className="primary-action" type="submit">Add</button></form>
            {watchlist.items.length ? <div className="watchlist-items">{watchlist.items.map((item) => <div key={item.id}><Link className="ticker-link" href={`/market?symbol=${encodeURIComponent(item.symbol)}`}>{item.symbol}</Link><button className="table-action" onClick={() => handleWatchlistRemove(item.symbol)}>Remove</button></div>)}</div> : <p className="panel-empty">Your research watchlist is empty.</p>}
          </section>
        </div>
      </section>
    </main>
  );
}
