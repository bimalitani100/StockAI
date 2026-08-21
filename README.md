# StockAI

StockAI is a production-minded stock research and portfolio-accounting platform built as a
hands-on software engineering project. Version 0.6 combines cash-backed portfolio accounting,
role-aware workspaces, auto-updating quotes, and interactive price history on top of append-only
trade and cash ledgers.

This is a development application, not a brokerage, tax engine, or source of investment advice.
It records user-entered activity and reads provisional development market data; it never executes trades.

## What works now

- Registration and server-enforced user/administrator roles.
- Append-only buy/sell history with chronological share validation.
- Cash deposits, withdrawals, dividends, and trusted opening funding.
- Cash-backed purchases and withdrawal protection with atomic rollback.
- Trade fees included in buy cost basis and deducted from sell proceeds.
- Weighted-average realized gain and current unrealized gain.
- Live USD valuation, total value, total return, and return rate.
- Auto-updating stock detail with an interactive 1D-to-MAX price chart.
- Click-through research from portfolio holdings, watchlist items, and admin holdings.
- Safe incomplete state when any holding lacks a usable quote—no misleading partial total.
- Private watchlists and audited admin access to holdings, transactions, and cash history.
- Data-preserving PostgreSQL migrations and idempotent local seed data.

## Accounting rules

- `cash balance = cash inflows + sell proceeds − purchases − trade fees − withdrawals`
- `net contributions = deposits + opening funding − withdrawals`
- Buy fees increase weighted-average cost; sell fees reduce realized proceeds.
- `total value = cash balance + current market value of all holdings`
- `total return = total value − net contributions`
- Return percentage is shown only when net contributions are positive.
- A portfolio total is shown only when every holding has a compatible USD quote.

Opening funding exists only to migrate pre-v0.5 activity. The migration calculates the maximum
historical cash shortfall required to fund existing trades, preserving the portfolio without
inventing a current negative cash balance.

## Repository map

```text
app/                         Next.js routes
components/                  React auth, user, admin, market, and accounting UI
lib/                         Typed frontend API clients
types/                       TypeScript API contracts
backend/app/api/             FastAPI dependencies and versioned routes
backend/app/models/          Account, trade, cash, holding, watchlist, and audit models
backend/app/services/        Ledger replay, accounting, valuation, auth, and market logic
backend/app/providers/       Replaceable market-data clients
backend/alembic/             Versioned, data-preserving migrations
backend/scripts/             Trusted local demo seed
backend/tests/               API, accounting, migration-boundary, and authorization tests
docs/                        Architecture, authorization, roadmap, and learning notes
```

## Run locally

Prerequisites: Docker Desktop, Node.js 22.13+ with npm, and Python 3.12+.

### 1. Start PostgreSQL

```bash
test -f .env.local || cp .env.example .env.local
docker compose up -d postgres
docker compose ps
```

StockAI exposes PostgreSQL on local port `5433`; the container listens on `5432` internally.

### 2. Upgrade and start the API

```bash
cd backend
./.venv/bin/python -m pip install -r requirements-dev.txt
./.venv/bin/alembic upgrade head
./.venv/bin/python -m scripts.seed_demo
./.venv/bin/uvicorn app.main:app --reload --port 8000
```

The v0.5 migration adds zero-fee defaults to existing trades and opening funding sufficient to
cover their historical cash requirement. Existing holdings, transactions, and watchlists remain intact.

Open `http://localhost:8000/docs` for the generated API explorer.

### 3. Start the web app

```bash
npm install
npm run dev
```

Open `http://localhost:3000/login`:

| Workspace | Email | Password |
| --- | --- | --- |
| Admin | `admin@stockai.local` | `StockAI123!` |
| User | `user@stockai.local` | `StockAI123!` |

For a new purchase, record a deposit first. Existing migrated positions begin with zero available
cash because opening funding exactly offsets their historical purchases.

## Current API surface

| Method | Route | Access | Purpose |
| --- | --- | --- | --- |
| `GET` | `/api/v1/portfolio/accounting` | Signed in | Cash, contributions, dividends, fees, and realized gain |
| `GET` | `/api/v1/portfolio/cash-events` | Signed in | Return the caller's cash ledger |
| `POST` | `/api/v1/portfolio/cash-events` | Signed in | Record deposit, withdrawal, or dividend |
| `GET` | `/api/v1/portfolio/valuation` | Signed in | Current USD value and return with completeness status |
| `POST` | `/api/v1/portfolio/transactions` | Signed in | Record a cash-validated buy/sell with optional fee |
| `GET` | `/api/v1/admin/users/{id}/portfolio` | Admin | Audit and view holdings, trades, cash, and accounting |
| `GET` | `/api/v1/market-history?symbol=NVDA&range=1d` | Public | Return chart-ready historical prices and range change |

The existing authentication, market summary, portfolio, watchlist, admin user, and audit endpoints
remain available through `/api/v1`.

## Deliberate limits

Stock splits, mergers, spin-offs, tax-lot selection, short positions, margin, multi-currency
conversion, time-weighted return, and money-weighted return are not modeled yet. StockAI reports a
simple since-inception return against net contributions—not a tax or institutional performance metric.

The current Yahoo Finance adapter is unofficial and intended for development/personal research.
The browser polls quotes every 15 seconds and refreshes the 1D chart every 60 seconds while visible,
but the upstream values can be delayed or throttled. A licensed streaming provider is required for
production tick-by-tick updates; the market-provider boundary is designed for that replacement.

## Verify

```bash
npm run lint
npm run test
cd backend && ./.venv/bin/pytest
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Authorization rules](docs/AUTHORIZATION.md)
- [Learning notes](docs/LEARNING.md)
- [Roadmap](docs/ROADMAP.md)
- [Changelog](CHANGELOG.md)
