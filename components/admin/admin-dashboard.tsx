"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { getAdminPortfolio, getAdminUsers, getAuditLog, getSession, logout } from "@/lib/auth-api";
import { ApiRequestError } from "@/lib/api";
import type { AuthUser } from "@/types/auth";
import type { AdminPortfolioView, AdminUserSummary, AuditLog } from "@/types/portfolio";

export function AdminDashboard() {
  const router = useRouter();
  const [admin, setAdmin] = useState<AuthUser | null>(null);
  const [users, setUsers] = useState<AdminUserSummary[]>([]);
  const [auditLog, setAuditLog] = useState<AuditLog[]>([]);
  const [selected, setSelected] = useState<AdminPortfolioView | null>(null);
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getSession(), getAdminUsers(), getAuditLog()])
      .then(([session, loadedUsers, logs]) => {
        if (session.user.role !== "admin") {
          router.replace("/dashboard");
          return;
        }
        setAdmin(session.user);
        setUsers(loadedUsers);
        setAuditLog(logs);
      })
      .catch((requestError: unknown) => {
        if (requestError instanceof ApiRequestError && requestError.status === 401) {
          router.replace("/login");
          return;
        }
        setError(requestError instanceof Error ? requestError.message : "Unable to load admin workspace.");
      });
  }, [router]);

  const filteredUsers = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return users;
    return users.filter(({ user }) =>
      `${user.full_name} ${user.email}`.toLowerCase().includes(query),
    );
  }, [search, users]);

  async function viewPortfolio(userId: string) {
    setError(null);
    try {
      const portfolio = await getAdminPortfolio(userId);
      setSelected(portfolio);
      setAuditLog(await getAuditLog());
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to view portfolio.");
    }
  }

  async function handleLogout() {
    await logout();
    router.replace("/login");
    router.refresh();
  }

  if (!admin) {
    return <main className="portal-loading">{error ?? "Loading the administration workspace…"}</main>;
  }

  const totalTrackedCost = users.reduce((total, user) => total + user.total_cost, 0);

  return (
    <main className="portal-shell admin-theme">
      <aside className="portal-sidebar">
        <Link className="portal-brand" href="/admin">StockAI <small>Admin</small></Link>
        <nav><a className="active" href="#users">Users</a><a href="#audit">Audit log</a><Link href="/market">Market search</Link></nav>
        <button className="text-action" onClick={handleLogout}>Sign out</button>
      </aside>

      <section className="portal-content">
        <header className="portal-header">
          <div><span className="kicker">ADMINISTRATION</span><h1>Platform overview.</h1></div>
          <span className="role-badge admin">Administrator</span>
        </header>
        {error && <p className="portal-error" role="alert">{error}</p>}

        <section className="metric-grid">
          <article><span>Registered users</span><strong>{users.length}</strong></article>
          <article><span>Tracked positions</span><strong>{users.reduce((total, user) => total + user.holding_count, 0)}</strong></article>
          <article><span>Aggregate cost basis</span><strong>${totalTrackedCost.toLocaleString(undefined, { maximumFractionDigits: 0 })}</strong></article>
        </section>

        <section className="portal-panel" id="users">
          <div className="panel-heading">
            <div><span className="kicker">AUTHORIZED VIEW</span><h2>User portfolios</h2></div>
            <input className="admin-search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search users" />
          </div>
          <div className="data-table-wrap">
            <table className="data-table">
              <thead><tr><th>User</th><th>Role</th><th>Holdings</th><th>Cost basis</th><th /></tr></thead>
              <tbody>
                {filteredUsers.map(({ user, holding_count, total_cost }) => (
                  <tr key={user.id}>
                    <td><strong>{user.full_name}</strong><small>{user.email}</small></td>
                    <td>{user.role}</td><td>{holding_count}</td><td>${total_cost.toLocaleString()}</td>
                    <td><button className="table-action" onClick={() => viewPortfolio(user.id)}>View holdings</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {selected && (
          <section className="portal-panel highlighted-panel">
            <div className="panel-heading">
              <div><span className="kicker">AUDITED ACCESS</span><h2>{selected.user.full_name}</h2><p>{selected.user.email}</p></div>
              <span className="audit-note">Access logged {new Date(selected.audited_at).toLocaleTimeString()}</span>
            </div>
            <div className="accounting-strip">
              <div><span>Cash balance</span><strong>${selected.accounting.cash_balance.toLocaleString()}</strong></div>
              <div><span>Net contributions</span><strong>${selected.accounting.net_contributions.toLocaleString()}</strong></div>
              <div><span>Realized gain</span><strong>${selected.accounting.realized_gain.toLocaleString()}</strong></div>
              <div><span>Dividends</span><strong>${selected.accounting.dividend_income.toLocaleString()}</strong></div>
            </div>
            {selected.portfolio.holdings.length ? (
              <div className="data-table-wrap"><table className="data-table"><thead><tr><th>Symbol</th><th>Quantity</th><th>Average cost</th><th>Cost basis</th></tr></thead><tbody>
                {selected.portfolio.holdings.map((holding) => <tr key={holding.id}><td><Link className="ticker-link" href={`/market?symbol=${encodeURIComponent(holding.symbol)}`}>{holding.symbol}</Link></td><td>{holding.quantity}</td><td>${holding.average_cost.toFixed(2)}</td><td>${holding.total_cost.toLocaleString()}</td></tr>)}
              </tbody></table></div>
            ) : <p className="panel-empty">This user has no recorded holdings.</p>}
            <h3 className="subsection-title">Transaction history</h3>
            {selected.transactions.length ? (
              <div className="data-table-wrap"><table className="data-table"><thead><tr><th>Type</th><th>Symbol</th><th>Quantity</th><th>Price</th><th>Fee</th><th>Date</th><th>Status</th></tr></thead><tbody>
                {selected.transactions.map((transaction) => <tr key={transaction.id}><td>{transaction.transaction_type.replace("_", " ")}</td><td><strong>{transaction.symbol}</strong></td><td>{transaction.quantity}</td><td>${transaction.price.toFixed(2)}</td><td>${transaction.fee.toFixed(2)}</td><td>{new Date(transaction.occurred_at).toLocaleDateString()}</td><td>{transaction.voided_at ? <span className="voided-label">Voided<small>{transaction.void_reason}</small></span> : "Active"}</td></tr>)}
              </tbody></table></div>
            ) : <p className="panel-empty">This user has no recorded transactions.</p>}
            <h3 className="subsection-title">Cash history</h3>
            {selected.cash_events.length ? (
              <div className="data-table-wrap"><table className="data-table"><thead><tr><th>Activity</th><th>Amount</th><th>Symbol</th><th>Date</th></tr></thead><tbody>
                {selected.cash_events.map((cashEvent) => <tr key={cashEvent.id}><td>{cashEvent.event_type.replace("_", " ")}</td><td>${cashEvent.amount.toFixed(2)}</td><td>{cashEvent.symbol ?? "Cash"}</td><td>{new Date(cashEvent.occurred_at).toLocaleDateString()}</td></tr>)}
              </tbody></table></div>
            ) : <p className="panel-empty">This user has no recorded cash activity.</p>}
          </section>
        )}

        <section className="portal-panel" id="audit">
          <div className="panel-heading"><div><span className="kicker">SECURITY TRAIL</span><h2>Recent admin access</h2></div></div>
          <div className="audit-list">
            {auditLog.length ? auditLog.map((log) => <div key={log.id}><span>{log.admin_email}</span><strong>{log.action}</strong><span>{log.target_email ?? "System"}</span><time>{new Date(log.created_at).toLocaleString()}</time></div>) : <p className="panel-empty">No administrative portfolio access recorded yet.</p>}
          </div>
        </section>
      </section>
    </main>
  );
}
