import type { AuthUser } from "@/types/auth";

export interface Holding {
  id: string;
  symbol: string;
  quantity: number;
  average_cost: number;
  total_cost: number;
  updated_at: string;
}

export interface Portfolio {
  id: string;
  name: string;
  holdings: Holding[];
  total_cost: number;
}

export type TransactionType = "buy" | "sell" | "opening_balance";

export interface PortfolioTransaction {
  id: string;
  symbol: string;
  transaction_type: TransactionType;
  quantity: number;
  price: number;
  fee: number;
  total_value: number;
  cash_effect: number;
  occurred_at: string;
  voided_at: string | null;
  void_reason: string | null;
}

export interface TransactionCreateResult {
  transaction: PortfolioTransaction;
  portfolio: Portfolio;
  accounting: AccountingSummary;
}

export type TransactionCorrectionResult = TransactionCreateResult;

export interface TaxLot {
  source_transaction_id: string;
  symbol: string;
  acquired_at: string;
  original_quantity: number;
  adjusted_quantity: number;
  remaining_quantity: number;
  cost_per_share: number;
  cost_basis: number;
}

export interface TaxLotInventory {
  policy: "fifo";
  lots: TaxLot[];
}

export type CorporateActionType = "stock_split";

export interface CorporateAction {
  id: string;
  action_type: CorporateActionType;
  symbol: string;
  new_shares: number;
  old_shares: number;
  ratio: number;
  occurred_at: string;
  voided_at: string | null;
  void_reason: string | null;
}

export interface CorporateActionCreateResult {
  corporate_action: CorporateAction;
  portfolio: Portfolio;
}

export type CorporateActionCorrectionResult = CorporateActionCreateResult;

export type CashEventType = "deposit" | "withdrawal" | "dividend" | "opening_balance";

export interface CashEvent {
  id: string;
  event_type: CashEventType;
  amount: number;
  symbol: string | null;
  occurred_at: string;
}

export interface AccountingSummary {
  cash_balance: number;
  net_contributions: number;
  dividend_income: number;
  realized_gain: number;
  trade_fees: number;
}

export interface CashEventCreateResult {
  cash_event: CashEvent;
  accounting: AccountingSummary;
}

export interface HoldingValuation {
  symbol: string;
  quantity: number;
  average_cost: number;
  cost_basis: number;
  current_price: number | null;
  market_value: number | null;
  unrealized_gain: number | null;
  change_percent: number | null;
  as_of: string | null;
  source: string | null;
  error: string | null;
}

export interface PortfolioValuation {
  accounting: AccountingSummary;
  holdings: HoldingValuation[];
  holdings_market_value: number | null;
  total_value: number | null;
  total_return: number | null;
  total_return_percent: number | null;
  is_complete: boolean;
  as_of: string;
}

export interface WatchlistItem {
  id: string;
  symbol: string;
  added_at: string;
}

export interface Watchlist {
  id: string;
  name: string;
  items: WatchlistItem[];
}

export interface AdminUserSummary {
  user: AuthUser;
  holding_count: number;
  total_cost: number;
}

export interface AdminPortfolioView {
  user: AuthUser;
  portfolio: Portfolio;
  transactions: PortfolioTransaction[];
  cash_events: CashEvent[];
  accounting: AccountingSummary;
  corporate_actions: CorporateAction[];
  audited_at: string;
}

export interface AuditLog {
  id: string;
  admin_email: string;
  target_email: string | null;
  action: string;
  created_at: string;
}
