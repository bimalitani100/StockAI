"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { MarketSummaryCard } from "@/components/market-summary-card";
import { getSession, logout } from "@/lib/auth-api";
import { ApiRequestError } from "@/lib/api";
import type { AuthUser } from "@/types/auth";

export function AuthenticatedMarketWorkspace({ initialSymbol }: { initialSymbol?: string }) {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getSession()
      .then((session) => setUser(session.user))
      .catch((requestError: unknown) => {
        if (requestError instanceof ApiRequestError && requestError.status === 401) {
          router.replace("/login");
          return;
        }
        setError(requestError instanceof Error ? requestError.message : "Unable to open market search.");
      });
  }, [router]);

  async function handleLogout() {
    await logout();
    router.replace("/login");
    router.refresh();
  }

  if (!user) {
    return <main className="portal-loading">{error ?? "Loading market search…"}</main>;
  }

  const isAdmin = user.role === "admin";
  const dashboardPath = isAdmin ? "/admin" : "/dashboard";

  return (
    <main className={`portal-shell${isAdmin ? " admin-theme" : ""}`}>
      <aside className="portal-sidebar">
        <Link className="portal-brand" href={dashboardPath}>
          StockAI <small>{isAdmin ? "Admin" : "v0.8"}</small>
        </Link>
        <nav>
          <Link href={dashboardPath}>{isAdmin ? "Administration" : "Performance"}</Link>
          <Link className="active" href="/market">Market search</Link>
        </nav>
        <button className="text-action" onClick={handleLogout}>Sign out</button>
      </aside>

      <section className="portal-content">
        <header className="portal-header">
          <div>
            <span className="kicker">AUTHENTICATED RESEARCH</span>
            <h1>Research the market.</h1>
          </div>
          <span className={`role-badge${isAdmin ? " admin" : ""}`}>
            {isAdmin ? "Administrator" : "User"}
          </span>
        </header>

        <section className="market-workspace-panel" aria-labelledby="workspace-title">
          <MarketSummaryCard initialSymbol={initialSymbol} />
        </section>
      </section>
    </main>
  );
}
