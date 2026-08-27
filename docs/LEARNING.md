# StockAI learning notes

## Concepts introduced in v0.5

- **Double-ledger boundary:** stock transactions and cash events describe different resources and remain separate.
- **Cash sufficiency:** each purchase or withdrawal must be fundable at its chronological point.
- **Atomic rollback:** an invalid transaction changes neither the ledger nor derived holdings.
- **Cost basis:** purchase price plus buy fees, allocated across shares using weighted average.
- **Realized gain:** net sale proceeds minus the average cost of shares sold.
- **Unrealized gain:** current market value minus remaining cost basis.
- **Net contributions:** external money added minus money withdrawn; dividends are returns, not contributions.
- **Valuation completeness:** aggregate totals are withheld when any required quote is missing or incompatible.
- **Migration funding:** existing trades receive only the minimum opening cash needed to avoid historical overdraft.

## Example

1. Deposit `$1,000`.
2. Buy `4` shares at `$100` with a `$4` fee.
3. Cash becomes `$596`; average cost becomes `$101` per share.
4. Sell `1` share at `$150` with a `$2` fee.
5. Net proceeds are `$148`, cash becomes `$744`, and realized gain is `$47` (`148 − 101`).
6. The remaining `3` shares keep their `$101` average cost.

## Why a deposit is required now

v0.4 tracked shares but did not model how purchases were funded. Continuing to allow unlimited
buys after introducing cash would make the new cash balance meaningless. v0.5 therefore requires
sufficient chronological cash. The migration funds old trades automatically; new purchases require
a user-entered deposit or prior sale proceeds.

## Why incomplete valuation hides the total

Suppose nine holdings can be valued and one cannot. Summing the nine is technically possible but
financially misleading: portfolio value and return would be understated by an unknown amount.
StockAI returns the per-symbol problem and refuses the aggregate claim.

## What is intentionally incomplete

The displayed return is a simple since-inception dollar/percentage result against net contributions.
It does not adjust for the timing of cash flows. Time-weighted return, money-weighted return, daily
price snapshots, benchmarks, mergers, spin-offs, currency conversion, and tax reporting
need additional models and tested rules before they belong in the interface.

## Concepts introduced by the auto-updating chart

- **Polling:** the browser asks for a fresh quote on a schedule. It feels live but is not a pushed trade stream.
- **Streaming:** a WebSocket provider pushes events as trades or aggregates arrive; this needs provider credentials and market-data entitlements.
- **Sampling interval:** a 1D chart can use minute points while multi-year charts use daily, weekly, or monthly points to control payload size.
- **Baseline:** 1D gain/loss compares with the previous close; longer ranges compare with the first available point in the selected window.
- **Page visibility:** automatic requests pause in background tabs to reduce upstream traffic and rate-limit risk.
- **Provider honesty:** freshness metadata and `is_realtime` travel with the data so the UI cannot silently present delayed data as real-time.

The current adapter polls an unofficial development source. A moving interface does not prove the
underlying data is real-time; delivery method, upstream latency, and licensing are separate concerns.

## Concepts introduced in v0.7

- **Tax lot:** one purchase creates one batch of shares with its own acquisition date and cost.
- **FIFO:** “first in, first out” means a sale consumes the oldest available lot before newer lots.
- **Ledger correction:** an incorrect trade is marked void with a reason; it is never silently deleted.
- **Projection rebuild:** holdings are recalculated from valid historical entries instead of manually edited.
- **Invariant:** a rule that must always remain true, such as shares and cash never becoming negative.
- **Safe correction:** StockAI temporarily applies a void, replays the full history, and rolls everything
  back if any later sale, purchase, or withdrawal becomes impossible.

## FIFO example

1. Buy `10` shares at `$100`.
2. Buy another `10` shares at `$200`.
3. Sell `5` shares.
4. FIFO removes `5` shares from the first `$100` lot.
5. The open inventory is now `5 × $100` and `10 × $200`, for a `$2,500` remaining cost basis.

FIFO is a deterministic accounting policy, not personalized tax advice. StockAI does not yet support
specific-lot selection, wash-sale calculations, jurisdiction-specific reporting, or tax filing.

## Concepts introduced in v0.8

- **Corporate action:** a company event that changes an investment without the user buying or selling.
- **Forward split:** each old share becomes more shares, such as `1` old share becoming `2` new shares.
- **Reverse split:** multiple old shares combine into fewer shares, such as `10` old shares becoming `1` new share.
- **Economic preservation:** a split changes quantity and cost per share, but not cash or total cost basis.
- **Chronological replay:** StockAI combines trades and splits by effective time, then recalculates the result.
- **Precision guard:** StockAI refuses a split if it would need to silently round away fractional shares.

## Stock-split example

1. Buy `10` shares at `$100` each. Total cost basis is `$1,000`.
2. Record a `2-for-1` split.
3. The position becomes `20` shares at `$50` cost per share.
4. Total cost basis is still `$1,000`, and cash does not move.
5. Selling `5` adjusted shares consumes `$250` of FIFO cost basis.

A split is not a buy because no new money enters the portfolio. Keeping it in a separate
corporate-action ledger makes that difference explicit and keeps the original trade history truthful.
Real brokers may pay cash instead of issuing some fractional shares after a reverse split. StockAI
does not model that cash-in-lieu event yet, so it rejects unsupported fractional results.

## Account-settings security

- **Reauthentication:** a signed-in user must still enter the current password before changing it.
- **Server ownership:** the settings request never sends a user ID; the session determines which account changes.
- **Email verification boundary:** changing an email is more sensitive than changing a display name because
  email controls login and recovery. StockAI keeps it read-only until verification is implemented.
- **Session revocation:** changing the stored password blocks future login with the old password, but the
  current stateless session model cannot yet invalidate every token already issued on other devices.
