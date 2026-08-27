import { apiRequest } from "@/lib/api";
import type { AuthResponse } from "@/types/auth";
import type {
  AdminPortfolioView,
  AdminUserSummary,
  AccountingSummary,
  AuditLog,
  CashEvent,
  CashEventCreateResult,
  CashEventType,
  CorporateAction,
  CorporateActionCorrectionResult,
  CorporateActionCreateResult,
  Portfolio,
  PortfolioValuation,
  PortfolioTransaction,
  TaxLotInventory,
  TransactionCorrectionResult,
  TransactionCreateResult,
  TransactionType,
  Watchlist,
} from "@/types/portfolio";

export function login(email: string, password: string): Promise<AuthResponse> {
  return apiRequest<AuthResponse>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function register(fullName: string, email: string, password: string): Promise<AuthResponse> {
  return apiRequest<AuthResponse>("/api/v1/auth/register", {
    method: "POST",
    body: JSON.stringify({ full_name: fullName, email, password }),
  });
}

export function logout(): Promise<void> {
  return apiRequest<void>("/api/v1/auth/logout", { method: "POST" });
}

export function getSession(): Promise<AuthResponse> {
  return apiRequest<AuthResponse>("/api/v1/auth/me");
}

export function updateProfile(fullName: string): Promise<AuthResponse> {
  return apiRequest<AuthResponse>("/api/v1/auth/me", {
    method: "PATCH",
    body: JSON.stringify({ full_name: fullName }),
  });
}

export function changePassword(currentPassword: string, newPassword: string): Promise<void> {
  return apiRequest<void>("/api/v1/auth/change-password", {
    method: "POST",
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  });
}

export function getPortfolio(): Promise<Portfolio> {
  return apiRequest<Portfolio>("/api/v1/portfolio");
}

export function getTransactions(): Promise<PortfolioTransaction[]> {
  return apiRequest<PortfolioTransaction[]>("/api/v1/portfolio/transactions");
}

export function getTaxLots(): Promise<TaxLotInventory> {
  return apiRequest<TaxLotInventory>("/api/v1/portfolio/tax-lots");
}

export function getCorporateActions(): Promise<CorporateAction[]> {
  return apiRequest<CorporateAction[]>("/api/v1/portfolio/corporate-actions");
}

export function recordStockSplit(
  symbol: string,
  newShares: number,
  oldShares: number,
  occurredAt: string,
): Promise<CorporateActionCreateResult> {
  return apiRequest<CorporateActionCreateResult>("/api/v1/portfolio/corporate-actions/stock-splits", {
    method: "POST",
    body: JSON.stringify({
      symbol,
      new_shares: newShares,
      old_shares: oldShares,
      occurred_at: occurredAt,
    }),
  });
}

export function voidCorporateAction(
  actionId: string,
  reason: string,
): Promise<CorporateActionCorrectionResult> {
  return apiRequest<CorporateActionCorrectionResult>(
    `/api/v1/portfolio/corporate-actions/${encodeURIComponent(actionId)}/void`,
    {
      method: "POST",
      body: JSON.stringify({ reason }),
    },
  );
}

export function recordTransaction(
  transactionType: Exclude<TransactionType, "opening_balance">,
  symbol: string,
  quantity: number,
  price: number,
  fee: number,
  occurredAt: string,
): Promise<TransactionCreateResult> {
  return apiRequest<TransactionCreateResult>("/api/v1/portfolio/transactions", {
    method: "POST",
    body: JSON.stringify({
      transaction_type: transactionType,
      symbol,
      quantity,
      price,
      fee,
      occurred_at: occurredAt,
    }),
  });
}

export function voidTransaction(
  transactionId: string,
  reason: string,
): Promise<TransactionCorrectionResult> {
  return apiRequest<TransactionCorrectionResult>(
    `/api/v1/portfolio/transactions/${encodeURIComponent(transactionId)}/void`,
    {
      method: "POST",
      body: JSON.stringify({ reason }),
    },
  );
}

export function getAccounting(): Promise<AccountingSummary> {
  return apiRequest<AccountingSummary>("/api/v1/portfolio/accounting");
}

export function getCashEvents(): Promise<CashEvent[]> {
  return apiRequest<CashEvent[]>("/api/v1/portfolio/cash-events");
}

export function recordCashEvent(
  eventType: Exclude<CashEventType, "opening_balance">,
  amount: number,
  occurredAt: string,
  symbol?: string,
): Promise<CashEventCreateResult> {
  return apiRequest<CashEventCreateResult>("/api/v1/portfolio/cash-events", {
    method: "POST",
    body: JSON.stringify({
      event_type: eventType,
      amount,
      occurred_at: occurredAt,
      ...(symbol ? { symbol } : {}),
    }),
  });
}

export function getPortfolioValuation(): Promise<PortfolioValuation> {
  return apiRequest<PortfolioValuation>("/api/v1/portfolio/valuation");
}

export function getWatchlist(): Promise<Watchlist> {
  return apiRequest<Watchlist>("/api/v1/watchlist");
}

export function addToWatchlist(symbol: string): Promise<Watchlist> {
  return apiRequest<Watchlist>(`/api/v1/watchlist/items/${encodeURIComponent(symbol)}`, {
    method: "PUT",
  });
}

export function removeFromWatchlist(symbol: string): Promise<Watchlist> {
  return apiRequest<Watchlist>(`/api/v1/watchlist/items/${encodeURIComponent(symbol)}`, {
    method: "DELETE",
  });
}

export function getAdminUsers(): Promise<AdminUserSummary[]> {
  return apiRequest<AdminUserSummary[]>("/api/v1/admin/users");
}

export function getAdminPortfolio(userId: string): Promise<AdminPortfolioView> {
  return apiRequest<AdminPortfolioView>(`/api/v1/admin/users/${userId}/portfolio`);
}

export function getAuditLog(): Promise<AuditLog[]> {
  return apiRequest<AuditLog[]>("/api/v1/admin/audit-log");
}
