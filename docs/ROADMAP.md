# Roadmap

## v0.1–v0.4 — Foundation through transaction ledger (complete)

- Next.js/FastAPI foundation and replaceable market-data provider
- PostgreSQL accounts, migrations, authenticated roles, and audited admin reads
- Append-only buy/sell history, derived holdings, and private watchlists

## v0.5 — Cash accounting and valuation (complete)

- Deposit, withdrawal, dividend, and trusted opening-funding events
- Trade fees and chronological cash sufficiency validation
- Weighted-average realized gain and fee-adjusted cost basis
- Live holding valuation, total value, total return, and return rate
- Explicit incomplete valuation when any quote is missing or non-USD
- Data-preserving funding migration for existing transaction history
- Admin read-only cash and accounting visibility under audit

## v0.6 — Live market research and CI (complete)

- Auto-updating quotes with explicit delayed-development-feed labeling
- Chart-ready history and interactive 1D, 1W, 1M, 3M, YTD, 1Y, 5Y, and MAX ranges
- Responsive gain/loss chart with hover details and previous-close baseline
- Portfolio, watchlist, and audited admin navigation into symbol research
- Visibility-aware polling that pauses background-tab requests
- GitHub Actions checks for frontend, backend, migrations, PostgreSQL, and Compose configuration

## v0.7 — Portfolio accuracy (complete)

- History-preserving trade corrections with a required reason
- Full ledger replay before accepting a correction
- FIFO realized gain and remaining holding cost basis
- Read-only open tax-lot inventory linked to source purchases
- Data-preserving migration from weighted-average holdings
- User correction controls and audited admin visibility

## v0.8 — Corporate actions (current)

- Separate user-owned corporate-action ledger
- Forward and reverse stock-split replay across FIFO lots
- Total cost-basis and cash preservation through splits
- History-preserving stock-split corrections with full safety replay
- Read-only audited administrator visibility
- Explicit rejection when fractional shares exceed supported precision

## Candidate next milestones

- **v0.9:** original visual redesign with a lively homepage, intentional motion, responsive dashboards, and a stronger non-template identity
- **v0.10:** time-weighted/money-weighted portfolio returns, persisted price snapshots, and benchmark comparison
- **v0.11:** explicit merger, spin-off, and fractional cash-in-lieu rules
- **v0.12:** email verification, recovery, throttling, privileged MFA, and managed identity evaluation
- **v0.13:** reproducible analytics and model evaluation before predictive UI
- **Later:** full-stack containers, deployment automation, observability, and AWS after runtime requirements are measured

Versions represent tested outcomes, not dates. Accounting completeness and reproducible market
history must exist before sophisticated performance claims or ML predictions.
