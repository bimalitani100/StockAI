"use client";

import { useEffect, useState } from "react";

type MarketSummary = {
  symbol: string;
  company_name: string;
  price: number;
  currency: string;
  change_percent: number;
  as_of: string;
  source: string;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function Home() {
  const [summary, setSummary] = useState<MarketSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    async function loadSummary() {
      try {
        const response = await fetch(`${API_URL}/api/v1/market-summary`, {
          signal: controller.signal,
        });
        if (!response.ok) throw new Error(`API returned ${response.status}`);
        setSummary((await response.json()) as MarketSummary);
      } catch (requestError) {
        if (requestError instanceof DOMException && requestError.name === "AbortError") return;
        setError("Start the API service to load the live demo response.");
      }
    }

    loadSummary();
    return () => controller.abort();
  }, []);

  const isPositive = (summary?.change_percent ?? 0) >= 0;

  return (
    <main>
      <nav className="nav" aria-label="Primary navigation">
        <a className="brand" href="#top" aria-label="StockAI home">
          <span className="brand-mark">S</span>
          StockAI
        </a>
        <span className="version">Foundation · v0.1.0</span>
      </nav>

      <section className="hero" id="top">
        <div className="eyebrow"><span /> BUILD LOG 001</div>
        <h1>Market intelligence,<br /><em>built in the open.</em></h1>
        <p className="lede">
          A production-minded stock research platform growing one tested,
          documented capability at a time.
        </p>
      </section>

      <section className="workspace" aria-labelledby="workspace-title">
        <div className="section-heading">
          <div>
            <span className="kicker">FIRST VERTICAL SLICE</span>
            <h2 id="workspace-title">Frontend meets API</h2>
          </div>
          <span className={`status ${summary ? "online" : ""}`}>
            <i /> {summary ? "API connected" : "Waiting for API"}
          </span>
        </div>

        <article className="quote-card" aria-live="polite">
          <div className="quote-topline">
            <span>MARKET SNAPSHOT</span>
            <span>{summary ? new Date(summary.as_of).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : "—"}</span>
          </div>
          {summary ? (
            <div className="quote-content">
              <div>
                <div className="symbol">{summary.symbol}</div>
                <div className="company">{summary.company_name}</div>
              </div>
              <div className="price-block">
                <div className="price">${summary.price.toFixed(2)}</div>
                <div className={isPositive ? "change positive" : "change negative"}>
                  {isPositive ? "+" : ""}{summary.change_percent.toFixed(2)}%
                </div>
              </div>
            </div>
          ) : (
            <div className="empty-state">
              <div className="pulse" />
              <div>
                <strong>{error ?? "Requesting market summary…"}</strong>
                <p>The UI is ready; the data comes from FastAPI on port 8000.</p>
              </div>
            </div>
          )}
          <div className="quote-footer">
            <span>GET /api/v1/market-summary</span>
            <span>{summary?.source ?? "Demo data · no external provider yet"}</span>
          </div>
        </article>
      </section>

      <section className="principles" aria-labelledby="principles-title">
        <span className="kicker">ENGINEERING PRINCIPLES</span>
        <h2 id="principles-title">Small surface. Strong foundation.</h2>
        <div className="principle-grid">
          <article><span>01</span><h3>Typed boundaries</h3><p>TypeScript and Pydantic make the data contract visible on both sides.</p></article>
          <article><span>02</span><h3>Versioned API</h3><p>The <code>/api/v1</code> prefix lets the backend evolve without surprise breakage.</p></article>
          <article><span>03</span><h3>Honest scope</h3><p>Static demo data proves the path before we choose a market-data provider.</p></article>
        </div>
      </section>

      <footer><span>StockAI · Learning by shipping</span><span>Next: persistence &amp; real market data</span></footer>
    </main>
  );
}
