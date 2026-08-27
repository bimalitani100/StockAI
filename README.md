# StockAI

StockAI is a production-minded stock research and portfolio-accounting platform built as a
hands-on software engineering project. Version 0.8 combines cash-backed portfolio accounting,
history-preserving corrections, FIFO tax lots, stock-split processing, role-aware workspaces,
auto-updating quotes, and interactive price history on top of auditable ledgers.

This is a development application, not a brokerage, tax engine, or source of investment advice.
It records user-entered activity and reads provisional development market data; it never executes trades.

## What works now

- Registration and server-enforced user/administrator roles.
- Profile menu with protected display-name and password settings.
- Buy/sell history with chronological share validation and history-preserving corrections.
- Cash deposits, withdrawals, dividends, and trusted opening funding.
- Cash-backed purchases and withdrawal protection with atomic rollback.
- Trade fees included in buy cost basis and deducted from sell proceeds.
- FIFO realized gain, remaining lot cost basis, and current unrealized gain.
- Read-only open tax-lot inventory linked to each source purchase.
- Forward and reverse stock splits with chronological FIFO replay and correction history.
- Live USD valuation, total value, total return, and return rate.
- Auto-updating stock detail with an interactive 1D-to-MAX price chart.
- Click-through research from portfolio holdings, watchlist items, and admin holdings.
- Safe incomplete state when any holding lacks a usable quote—no misleading partial total.
- Private watchlists and audited admin access to holdings, transactions, corporate actions, and cash history.
- Data-preserving PostgreSQL migrations and idempotent local seed data.

## Accounting rules

- `cash balance = cash inflows + sell proceeds − purchases − trade fees − withdrawals`
- `net contributions = deposits + opening funding − withdrawals`
- Buy fees enter the purchase lot cost; sell fees reduce realized proceeds.
- FIFO sales consume the oldest open purchase lot first.
- Voided trades remain visible but no longer affect shares, cash, fees, or gains.
- A split changes share quantity and cost per share but preserves total cost basis and cash.
- Voided splits remain visible but no longer adjust shares or tax lots.
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
backend/app/models/          Account, trade, cash, corporate-action, holding, watchlist, and audit models
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

The v0.8 migration adds a separate corporate-action ledger. Existing users, holdings, transactions,
cash events, tax-lot results, and watchlists remain intact.

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
| `PATCH` | `/api/v1/auth/me` | Signed in | Update the caller's normalized display name |
| `POST` | `/api/v1/auth/change-password` | Signed in | Change password after verifying the current password |
| `GET` | `/api/v1/portfolio/accounting` | Signed in | Cash, contributions, dividends, fees, and realized gain |
| `GET` | `/api/v1/portfolio/cash-events` | Signed in | Return the caller's cash ledger |
| `POST` | `/api/v1/portfolio/cash-events` | Signed in | Record deposit, withdrawal, or dividend |
| `GET` | `/api/v1/portfolio/valuation` | Signed in | Current USD value and return with completeness status |
| `GET` | `/api/v1/portfolio/tax-lots` | Signed in | Return the caller's open FIFO lots |
| `GET` | `/api/v1/portfolio/corporate-actions` | Signed in | Return the caller's stock-split history |
| `POST` | `/api/v1/portfolio/corporate-actions/stock-splits` | Signed in | Record a forward or reverse split |
| `POST` | `/api/v1/portfolio/corporate-actions/{id}/void` | Signed in | Void a split while preserving its history |
| `POST` | `/api/v1/portfolio/transactions` | Signed in | Record a cash-validated buy/sell with optional fee |
| `POST` | `/api/v1/portfolio/transactions/{id}/void` | Signed in | Void the caller's trade with a preserved reason |
| `GET` | `/api/v1/admin/users/{id}/portfolio` | Admin | Audit and view holdings, trades, cash, and accounting |
| `GET` | `/api/v1/market-history?symbol=NVDA&range=1d` | Public | Return chart-ready historical prices and range change |

The existing authentication, market summary, portfolio, watchlist, admin user, and audit endpoints
remain available through `/api/v1`.

## Deliberate limits

Mergers, spin-offs, cash-in-lieu for fractional split shares, specific-lot selection, short positions,
margin, multi-currency conversion, time-weighted return, and money-weighted return are not modeled yet.
StockAI rejects a split that cannot be represented at its six-decimal share precision instead of
silently rounding it. It reports a simple since-inception return against net contributions—not a tax
or institutional performance metric.

Email changes remain locked until address verification and account-recovery protections exist.
Password changes update future authentication but do not yet revoke every previously issued stateless
session token; managed session revocation is part of the later authentication-hardening milestone.

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
