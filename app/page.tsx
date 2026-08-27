import { MarketSummaryCard } from "@/components/market-summary-card";

export default function Home() {
  return (
    <main>
      <nav className="nav" aria-label="Primary navigation">
        <a className="brand" href="#top" aria-label="StockAI home">
          <span className="brand-mark">S</span>
          StockAI
        </a>
        <div className="nav-actions"><span className="version">Corporate actions · v0.8.0</span><a href="/login">Sign in</a></div>
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
        <MarketSummaryCard />
      </section>

      <section className="principles" aria-labelledby="principles-title">
        <span className="kicker">ENGINEERING PRINCIPLES</span>
        <h2 id="principles-title">Small surface. Strong foundation.</h2>
        <div className="principle-grid">
          <article><span>01</span><h3>Typed boundaries</h3><p>TypeScript and Pydantic make the data contract visible on both sides.</p></article>
          <article><span>02</span><h3>Versioned API</h3><p>The <code>/api/v1</code> prefix lets the backend evolve without surprise breakage.</p></article>
          <article><span>03</span><h3>Honest scope</h3><p>Performance totals disappear when complete, compatible market quotes are unavailable.</p></article>
        </div>
      </section>

      <footer><span>StockAI · Learning by shipping</span><span>Next: original interface redesign</span></footer>
    </main>
  );
}
