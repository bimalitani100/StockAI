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
price snapshots, benchmarks, corporate actions, tax lots, currency conversion, and tax reporting
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
