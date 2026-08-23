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

## v0.7 — Portfolio accuracy (current)

- History-preserving trade corrections with a required reason
- Full ledger replay before accepting a correction
- FIFO realized gain and remaining holding cost basis
- Read-only open tax-lot inventory linked to source purchases
- Data-preserving migration from weighted-average holdings
- User correction controls and audited admin visibility

## Candidate next milestones

- **v0.8:** stock splits first, then explicit rules for mergers and spin-offs
- **v0.9:** time-weighted/money-weighted portfolio returns, persisted price snapshots, and benchmark comparison
- **v0.10:** email verification, recovery, throttling, privileged MFA, and managed identity evaluation
- **v0.11:** reproducible analytics and model evaluation before predictive UI
- **Later:** full-stack containers, deployment automation, observability, and AWS after runtime requirements are measured

Versions represent tested outcomes, not dates. Accounting completeness and reproducible market
history must exist before sophisticated performance claims or ML predictions.
