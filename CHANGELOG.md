# Changelog

All notable changes follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions use [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- User-owned trade corrections that preserve the original transaction, correction time, and reason.
- Safety replay that rejects a correction when it would create a historical oversell or cash deficit.
- FIFO tax-lot inventory API and dashboard view with remaining quantity and per-lot cost basis.
- PostgreSQL migration that adds correction metadata and rebuilds existing holding costs under FIFO.

### Changed

- Replaced weighted-average sale accounting with an explicit FIFO policy for realized gains and remaining cost basis.
- Exposed correction status to audited administrator transaction views without granting write access.

## [0.6.0] - 2026-08-20

### Added

- Chart-ready market history for 1D, 1W, 1M, 3M, YTD, 1Y, 5Y, and MAX windows.
- Interactive gain/loss chart with hover details, previous-close baseline, and responsive range controls.
- Automatic 15-second quote polling and 60-second intraday chart refresh while the page is visible.
- Direct research links from user holdings, watchlist items, and audited admin holdings.

### Fixed

- Kept admin and user market search inside the authenticated portal instead of sending signed-in users to the public landing page.
- Made portal brand links return to the correct role-specific dashboard.
- Added explicit high-contrast text colors to the dark market quote card.
- Labeled the current Yahoo adapter as delayed development data instead of implying exchange-grade real-time delivery.

## [0.5.0] - 2026-08-19

### Added

- Deposit, withdrawal, dividend, and trusted opening-funding cash events.
- Trade fees, cash-backed purchases, and chronological overdraft protection.
- Fee-adjusted weighted-average cost and realized-gain calculations.
- Live USD holdings valuation, total value, total return, and return percentage.
- Explicit incomplete valuation responses when a required quote is unavailable or non-USD.
- Audited admin visibility into cash history and accounting summaries.
- Accounting, fee, rollback, dividend, valuation, and incomplete-quote tests.

### Changed

- Migrated existing v0.4 activity with zero-fee trades and minimum required opening funding.
- Expanded the user dashboard into cash, trading, holdings, valuation, and performance workflows.

## [0.4.0] - 2026-08-19

### Added

- Append-only buy, sell, and trusted opening-balance transaction records.
- Chronological holding projection with weighted-average cost and oversell rollback.
- Private default watchlists with idempotent add and remove operations.
- Admin read-only transaction history under the existing portfolio audit event.
- A data-preserving migration that backfills v0.3 holdings and existing account watchlists.
- Transaction, backdating, rollback, watchlist privacy, and ownership tests.

### Changed

- Replaced direct holding edits with transaction-driven, read-only holdings.
- Expanded the user workspace with transaction activity and watchlist panels.
- Updated PostgreSQL 18 persistence to its required `/var/lib/postgresql` volume target.
- Standardized the local host database port on `5433` to avoid a native `5432` conflict.

## [0.3.0] - 2026-08-19

### Added

- PostgreSQL-backed users, portfolios, holdings, and administrator audit events.
- Alembic schema migration, local PostgreSQL Compose service, and idempotent demo seed.
- Registration, login, logout, current-session, portfolio, and admin APIs.
- Dedicated user and administrator workspaces with role-aware routing.
- Server-side role enforcement and audited admin portfolio reads.
- Authentication, ownership, authorization, session, and admin-access tests.

### Changed

- Advanced the application version to 0.3.0 and documented the local database workflow.
- Expanded frontend API handling to include credentialed JSON requests and typed API errors.
- Made application configuration load from the root `.env.local` file for both services.

## [0.2.0] - 2026-08-19

### Added

- Searchable current market summaries for validated ticker symbols.
- Replaceable external market-data provider adapter.
- Explicit invalid-symbol, not-found, and provider-unavailable API behavior.
- Deterministic endpoint and provider parsing tests.

### Changed

- Replaced the initial Next.js-compatible Vinext runtime with the official Next.js package.
- Removed unused Cloudflare, Vite, Worker, Drizzle, and starter-auth infrastructure.
- Separated frontend API access, interactive UI, backend routes, schemas, services, and configuration into explicit modules.
- Updated the dashboard from a static NVDA demonstration to an interactive market lookup.

## [0.1.0] - 2026-08-12

### Added

- Responsive StockAI foundation dashboard.
- FastAPI health and versioned market-summary endpoints.
- Typed frontend-to-backend request with explicit loading and error states.
- Backend contract tests, architecture diagram, learning notes, roadmap, and local setup guide.
