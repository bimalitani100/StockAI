"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useEffect, useRef, useState } from "react";

import {
  addToWatchlist,
  getAccounting,
  getCashEvents,
  getCorporateActions,
  getPortfolio,
  getPortfolioValuation,
  getSession,
  getTaxLots,
  getTransactions,
  getWatchlist,
  logout,
  recordCashEvent,
  recordStockSplit,
  recordTransaction,
  removeFromWatchlist,
  voidTransaction,
  voidCorporateAction,
} from "@/lib/auth-api";
import { ApiRequestError } from "@/lib/api";
import type { AuthUser } from "@/types/auth";
import type {
  AccountingSummary,
  CashEvent,
  CashEventType,
  CorporateAction,
  Portfolio,
  PortfolioTransaction,
  PortfolioValuation,
  TaxLotInventory,
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

function userInitials(fullName: string): string {
  const initials = fullName
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
  return initials || "U";
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
  const [taxLots, setTaxLots] = useState<TaxLotInventory | null>(null);
  const [corporateActions, setCorporateActions] = useState<CorporateAction[] | null>(null);
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
  const [correctingTransactionId, setCorrectingTransactionId] = useState<string | null>(null);
  const [correctionReason, setCorrectionReason] = useState("");
  const [splitSymbol, setSplitSymbol] = useState("");
  const [splitNewShares, setSplitNewShares] = useState("2");
  const [splitOldShares, setSplitOldShares] = useState("1");
  const [splitOccurredAt, setSplitOccurredAt] = useState(localDateTimeValue);
  const [correctingActionId, setCorrectingActionId] = useState<string | null>(null);
  const [actionCorrectionReason, setActionCorrectionReason] = useState("");

  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [profileMenuOpen, setProfileMenuOpen] = useState(false);
  const profileMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    Promise.all([
      getSession(),
      getPortfolio(),
      getTransactions(),
      getWatchlist(),
      getAccounting(),
      getCashEvents(),
      getTaxLots(),
      getCorporateActions(),
    ])
      .then(([
        session,
        loadedPortfolio,
        loadedTransactions,
        loadedWatchlist,
        loadedAccounting,
        loadedCashEvents,
        loadedTaxLots,
        loadedCorporateActions,
      ]) => {
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
        setTaxLots(loadedTaxLots);
        setCorporateActions(loadedCorporateActions);
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

  useEffect(() => {
    if (!profileMenuOpen) return;

    function closeOnOutsideClick(event: PointerEvent) {
      if (event.target instanceof Node && !profileMenuRef.current?.contains(event.target)) {
        setProfileMenuOpen(false);
      }
    }

    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === "Escape") setProfileMenuOpen(false);
    }

    document.addEventListener("pointerdown", closeOnOutsideClick);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOnOutsideClick);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [profileMenuOpen]);

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
      setTaxLots(await getTaxLots());
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

  async function handleTransactionCorrection(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!correctingTransactionId) return;

    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const result = await voidTransaction(correctingTransactionId, correctionReason);
      setPortfolio(result.portfolio);
      setAccounting(result.accounting);
      const [loadedTransactions, loadedTaxLots] = await Promise.all([
        getTransactions(),
        getTaxLots(),
      ]);
      setTransactions(loadedTransactions);
      setTaxLots(loadedTaxLots);
      setCorrectingTransactionId(null);
      setCorrectionReason("");
      setNotice(`The ${result.transaction.symbol} trade was voided; its original record was preserved.`);
      await refreshValuation();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to correct transaction.");
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

  async function handleStockSplitSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const result = await recordStockSplit(
        splitSymbol.trim().toUpperCase(),
        Number(splitNewShares),
        Number(splitOldShares),
        new Date(splitOccurredAt).toISOString(),
      );
      setPortfolio(result.portfolio);
      const [loadedActions, loadedTaxLots] = await Promise.all([
        getCorporateActions(),
        getTaxLots(),
      ]);
      setCorporateActions(loadedActions);
      setTaxLots(loadedTaxLots);
      setNotice(`${result.corporate_action.new_shares}-for-${result.corporate_action.old_shares} split recorded for ${result.corporate_action.symbol}.`);
      setSplitSymbol("");
      setSplitNewShares("2");
      setSplitOldShares("1");
      await refreshValuation();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to record stock split.");
    } finally {
      setSaving(false);
    }
  }

  async function handleCorporateActionCorrection(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!correctingActionId) return;

    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const result = await voidCorporateAction(correctingActionId, actionCorrectionReason);
      setPortfolio(result.portfolio);
      const [loadedActions, loadedTaxLots] = await Promise.all([
        getCorporateActions(),
        getTaxLots(),
      ]);
      setCorporateActions(loadedActions);
      setTaxLots(loadedTaxLots);
      setCorrectingActionId(null);
      setActionCorrectionReason("");
      setNotice(`The ${result.corporate_action.symbol} split was voided; its original record was preserved.`);
      await refreshValuation();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to correct stock split.");
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

  if (!user || !portfolio || !transactions || !watchlist || !accounting || !cashEvents || !taxLots || !corporateActions) {
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
        <Link className="portal-brand" href="/dashboard">StockAI <small>v0.8 development</small></Link>
        <nav>
          <a className="active" href="#overview">Performance</a>
          <a href="#cash">Cash</a>
          <a href="#transactions">Transactions</a>
          <a href="#corporate-actions">Stock splits</a>
          <a href="#holdings">Holdings</a>
          <a href="#watchlist">Watchlist</a>
          <Link href="/market">Market search</Link>
        </nav>
        <div className="sidebar-profile-wrap" ref={profileMenuRef}>
          {profileMenuOpen && (
            <div className="sidebar-profile-menu" role="menu" aria-label="Account options">
              <Link role="menuitem" href="/settings" onClick={() => setProfileMenuOpen(false)}>
                <strong>Settings</strong>
                <small>Profile and password</small>
              </Link>
              <button role="menuitem" type="button" onClick={handleLogout}>Sign out</button>
            </div>
          )}
          <button
            className="sidebar-profile"
            type="button"
            aria-label="Open account menu"
            aria-haspopup="menu"
            aria-expanded={profileMenuOpen}
            onClick={() => setProfileMenuOpen((isOpen) => !isOpen)}
          >
            <span className="profile-avatar" aria-hidden="true">{userInitials(user.full_name)}</span>
            <span className="profile-details">
              <strong>{user.full_name}</strong>
              <small title={user.email}>{user.email}</small>
            </span>
            <span className="profile-chevron" aria-hidden="true">{profileMenuOpen ? "×" : "•••"}</span>
          </button>
        </div>
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

        <section className="portal-panel" id="corporate-actions">
          <div className="panel-heading">
            <div>
              <span className="kicker">CORPORATE-ACTION LEDGER</span>
              <h2>Record a stock split</h2>
              <p>A 2-for-1 split doubles shares and halves cost per share without changing total cost or cash.</p>
            </div>
          </div>
          <form className="holding-form split-form" onSubmit={handleStockSplitSubmit}>
            <label>Symbol<input value={splitSymbol} onChange={(event) => setSplitSymbol(event.target.value)} placeholder="AAPL" maxLength={10} required /></label>
            <label>New shares<input type="number" min="1" step="1" value={splitNewShares} onChange={(event) => setSplitNewShares(event.target.value)} required /></label>
            <label>For old shares<input type="number" min="1" step="1" value={splitOldShares} onChange={(event) => setSplitOldShares(event.target.value)} required /></label>
            <label>Effective date and time<input type="datetime-local" value={splitOccurredAt} onChange={(event) => setSplitOccurredAt(event.target.value)} required /></label>
            <button className="primary-action" type="submit" disabled={saving}>{saving ? "Recording…" : "Record split"}</button>
          </form>
          <div className="split-guide" role="note">
            <strong>{splitNewShares || "?"}-for-{splitOldShares || "?"}</strong>
            <div>
              <span>{Number(splitNewShares) >= Number(splitOldShares) ? "Forward split: share quantity increases." : "Reverse split: share quantity decreases."}</span>
              <small> Use the company&apos;s official effective date. StockAI currently rejects splits that require unsupported fractional-share rounding.</small>
            </div>
          </div>
          {corporateActions.length ? (
            <div className="transaction-list corporate-action-list">
              {corporateActions.map((action) => (
                <article className={action.voided_at ? "is-voided" : undefined} key={action.id}>
                  <span className="transaction-type stock-split">Split</span>
                  <strong>{action.symbol}</strong>
                  <span>
                    {action.new_shares}-for-{action.old_shares} ({action.ratio.toLocaleString()}× shares)
                    {action.voided_at && <small>Voided: {action.void_reason}</small>}
                  </span>
                  <div className="transaction-actions">
                    <time>{new Date(action.occurred_at).toLocaleDateString()}</time>
                    {!action.voided_at && (
                      <button
                        className="table-action"
                        type="button"
                        onClick={() => {
                          setCorrectingActionId(action.id);
                          setActionCorrectionReason("");
                        }}
                      >
                        Correct
                      </button>
                    )}
                  </div>
                  {correctingActionId === action.id && (
                    <form className="correction-form" onSubmit={handleCorporateActionCorrection}>
                      <label>
                        Why is this split incorrect?
                        <input
                          value={actionCorrectionReason}
                          onChange={(event) => setActionCorrectionReason(event.target.value)}
                          minLength={3}
                          maxLength={500}
                          required
                        />
                      </label>
                      <p>The record remains visible, but it stops adjusting shares and cost basis.</p>
                      <button className="danger-action" type="submit" disabled={saving}>Void split</button>
                      <button className="table-action" type="button" onClick={() => setCorrectingActionId(null)}>Cancel</button>
                    </form>
                  )}
                </article>
              ))}
            </div>
          ) : <p className="panel-empty">No stock splits recorded yet.</p>}
        </section>

        <section className="portal-panel" id="holdings">
          <div className="panel-heading"><div><span className="kicker">CALCULATED SNAPSHOT</span><h2>Portfolio holdings</h2><p>Read-only positions derived from your transaction ledger.</p></div></div>
          {portfolio.holdings.length ? (
            <div className="data-table-wrap"><table className="data-table"><thead><tr><th>Symbol</th><th>Quantity</th><th>Average cost</th><th>Cost basis</th></tr></thead><tbody>
              {portfolio.holdings.map((holding) => <tr key={holding.id}><td><Link className="ticker-link" href={`/market?symbol=${encodeURIComponent(holding.symbol)}`}>{holding.symbol}</Link></td><td>{holding.quantity.toLocaleString()}</td><td>{money(holding.average_cost)}</td><td>{money(holding.total_cost)}</td></tr>)}
            </tbody></table></div>
          ) : <p className="panel-empty">No holdings yet. Deposit cash, then record your first buy.</p>}
        </section>

        <section className="portal-panel" id="tax-lots">
          <div className="panel-heading">
            <div>
              <span className="kicker">FIFO INVENTORY</span>
              <h2>Open tax lots</h2>
              <p>Oldest shares are sold first; each remaining purchase keeps its own cost basis.</p>
            </div>
            <span className="lot-policy">Policy: {taxLots.policy.toUpperCase()}</span>
          </div>
          {taxLots.lots.length ? (
            <div className="data-table-wrap">
              <table className="data-table">
                <thead><tr><th>Symbol</th><th>Acquired</th><th>Original shares</th><th>Split-adjusted</th><th>Remaining</th><th>Cost/share</th><th>Open cost basis</th></tr></thead>
                <tbody>
                  {taxLots.lots.map((lot) => (
                    <tr key={lot.source_transaction_id}>
                      <td><Link className="ticker-link" href={`/market?symbol=${encodeURIComponent(lot.symbol)}`}>{lot.symbol}</Link></td>
                      <td>{new Date(lot.acquired_at).toLocaleDateString()}</td>
                      <td>{lot.original_quantity.toLocaleString()}</td>
                      <td>{lot.adjusted_quantity.toLocaleString()}</td>
                      <td>{lot.remaining_quantity.toLocaleString()}</td>
                      <td>{money(lot.cost_per_share)}</td>
                      <td>{money(lot.cost_basis)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : <p className="panel-empty">Open lots appear after you record a purchase.</p>}
        </section>

        <div className="portal-grid">
          <section className="portal-panel">
            <div className="panel-heading"><div><span className="kicker">LEDGER</span><h2>Recent trades</h2></div></div>
            {transactions.length ? (
              <div className="transaction-list">
                {transactions.map((transaction) => (
                  <article className={transaction.voided_at ? "is-voided" : undefined} key={transaction.id}>
                    <span className={`transaction-type ${transaction.transaction_type}`}>{transactionLabel(transaction.transaction_type)}</span>
                    <strong>{transaction.symbol}</strong>
                    <span>
                      {transaction.quantity.toLocaleString()} × {money(transaction.price)}
                      {transaction.fee ? ` + ${money(transaction.fee)} fee` : ""}
                      {transaction.voided_at && <small>Voided: {transaction.void_reason}</small>}
                    </span>
                    <div className="transaction-actions">
                      <time>{new Date(transaction.occurred_at).toLocaleDateString()}</time>
                      {!transaction.voided_at && transaction.transaction_type !== "opening_balance" && (
                        <button
                          className="table-action"
                          type="button"
                          onClick={() => {
                            setCorrectingTransactionId(transaction.id);
                            setCorrectionReason("");
                          }}
                        >
                          Correct
                        </button>
                      )}
                    </div>
                    {correctingTransactionId === transaction.id && (
                      <form className="correction-form" onSubmit={handleTransactionCorrection}>
                        <label>
                          Why is this trade incorrect?
                          <input
                            value={correctionReason}
                            onChange={(event) => setCorrectionReason(event.target.value)}
                            minLength={3}
                            maxLength={500}
                            required
                          />
                        </label>
                        <p>The original remains visible, but it stops affecting shares, cash, and gains.</p>
                        <button className="danger-action" type="submit" disabled={saving}>Void trade</button>
                        <button
                          className="table-action"
                          type="button"
                          onClick={() => setCorrectingTransactionId(null)}
                        >
                          Cancel
                        </button>
                      </form>
                    )}
                  </article>
                ))}
              </div>
            ) : <p className="panel-empty">No transactions recorded yet.</p>}
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
