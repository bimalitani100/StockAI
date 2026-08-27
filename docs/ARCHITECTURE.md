# StockAI architecture

## v0.8 system context

```mermaid
flowchart LR
  U["User or administrator"] --> W["Next.js web app"]
  W -->|"JSON + HttpOnly session"| A["FastAPI service"]
  A -->|"Atomic ledger updates"| P[(PostgreSQL)]
  A -->|"Quote adapter"| Y["Development market source"]
  Y -->|"Quote + sampled history"| A
  P --> V["Accounting and valuation service"]
  Y --> V
  V --> A
  A -. "future" .-> M["Analytics and ML services"]
```

The valid trade ledger records user trades; the cash ledger controls money; the corporate-action
ledger records company events such as stock splits. Holdings and open FIFO lots are rebuildable
projections of those chronological records. A corrected trade or split stays visible with a void time
and reason but is excluded from calculations. Valuation joins accounting state with current quotes
but does not persist or alter any ledger.

## Trade correction flow

```mermaid
sequenceDiagram
  participant B as Browser
  participant A as FastAPI
  participant D as PostgreSQL
  B->>A: POST transaction/id/void with reason
  A->>D: Lock caller's portfolio
  A->>D: Mark original trade void
  A->>D: Replay FIFO shares and chronological cash
  alt Every invariant remains valid
    A->>D: Rebuild holding projection and commit
    A-->>B: Corrected trade, portfolio, accounting
  else A later event becomes impossible
    A->>D: Roll back correction and projection
    A-->>B: 409 Conflict
  end
```

Corrections never update the original quantity, price, symbol, fee, or occurrence time. This keeps
the user and audited administrators able to see what was entered and why it stopped affecting results.

## Stock-split replay flow

```mermaid
sequenceDiagram
  participant B as Browser
  participant A as FastAPI
  participant D as PostgreSQL
  B->>A: POST stock split with symbol, terms, and effective time
  A->>D: Lock caller's portfolio
  A->>D: Append corporate-action record
  A->>D: Replay trades and actions chronologically
  alt Shares remain valid and exactly representable
    A->>D: Rebuild holdings and commit
    A-->>B: Corporate action and updated portfolio
  else No shares, historical oversell, or unsupported fraction
    A->>D: Roll back action and projection
    A-->>B: 409 Conflict
  end
```

For identical timestamps, StockAI applies the corporate action before the trade. A split multiplies
each open lot's share quantities by `new shares / old shares` and divides its per-share cost by the
same ratio. Total lot cost, cash, and already-realized gain do not change.

## Auto-updating research flow

```mermaid
sequenceDiagram
  participant B as Browser chart
  participant A as FastAPI
  participant Y as Development market source
  B->>A: GET summary every 15 seconds while visible
  A->>Y: Request current chart metadata
  Y-->>A: Delayed/development quote
  A-->>B: Typed summary + freshness metadata
  B->>A: GET selected price range
  A->>Y: Request sampled historical series
  Y-->>A: Timestamped close values
  A-->>B: Normalized chart points and baseline
```

This is polling, not streaming. The UI never claims tick-level real-time delivery because the
development provider offers no production service-level guarantee. `MarketDataProvider` owns both
summary and history operations so a future licensed adapter can replace the upstream source while
keeping the FastAPI and React contracts stable. A production WebSocket fan-out would live behind
the same boundary rather than exposing a vendor key to browsers.

## Funded transaction flow

```mermaid
sequenceDiagram
  participant B as Browser
  participant A as FastAPI
  participant D as PostgreSQL
  B->>A: POST buy with quantity, price, fee
  A->>D: Lock caller's portfolio
  A->>D: Append trade
  A->>D: Replay symbol history
  A->>D: Replay chronological cash timeline
  alt Shares and cash are valid
    A->>D: Update holding projection and commit
    A-->>B: Transaction, portfolio, accounting
  else Shares or cash are insufficient
    A->>D: Roll back all changes
    A-->>B: 409 Conflict
  end
```

Cash inflows at an identical timestamp are evaluated before purchases; sells are evaluated before
withdrawals. This deterministic priority lets migration opening funding cover a legacy purchase
at the same recorded time.

## Valuation completeness

```mermaid
flowchart TD
  H["Current holdings"] --> Q["Fetch one quote per symbol"]
  Q --> C{"Every quote available and USD?"}
  C -->|Yes| T["Publish market value and return"]
  C -->|No| I["Return per-position errors; hide total"]
```

Partial values can be more dangerous than no value: omitting an unavailable holding would make
the portfolio look smaller and distort return. v0.5 therefore exposes individual quote failures
but sets aggregate valuation and return fields to `null` unless the valuation is complete.

## Persistent model additions

```mermaid
erDiagram
  PORTFOLIO ||--o{ PORTFOLIO_TRANSACTION : records
  PORTFOLIO ||--o{ CORPORATE_ACTION : records
  PORTFOLIO ||--o{ CASH_EVENT : records
  PORTFOLIO ||--o{ HOLDING : projects
  PORTFOLIO_TRANSACTION {
    string transaction_type
    string symbol
    decimal quantity
    decimal price
    decimal fee
    datetime occurred_at
    datetime voided_at nullable
    string void_reason nullable
  }
  CASH_EVENT {
    string event_type
    decimal amount
    string symbol nullable
    datetime occurred_at
  }
  CORPORATE_ACTION {
    string action_type
    string symbol
    decimal new_shares
    decimal old_shares
    datetime occurred_at
    datetime voided_at nullable
    string void_reason nullable
  }
```

`deposit`, `withdrawal`, and `opening_balance` affect net contributions. `dividend` affects cash
and return but not contributions. Buy fees enter cost basis; sell fees reduce realized proceeds.

## FIFO lot policy and performance limits

Each buy or opening transaction creates one lot whose per-share cost includes its allocated buy fee.
A sale consumes the oldest open shares first; its fee reduces realized proceeds. Holdings store the
average cost of only the remaining FIFO lots, while the API can rebuild each individual lot from the
ledger. Lots are derived rather than persisted, avoiding two competing sources of truth.

StockAI uses `total value − net contributions` for since-inception dollar return. This is internally
consistent for the modeled events, but it is not time-weighted return, internal rate of return, tax
reporting, or specific-lot tax advice. Mergers, spin-offs, cash-in-lieu, shorts, margin, and currency
conversion remain future work.
