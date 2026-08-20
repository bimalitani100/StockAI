import type { MarketHistory, MarketRange, MarketSummary } from "@/types/market";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type ApiError = { detail?: string | Array<{ msg?: string }> };

export class ApiRequestError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
  }
}

function errorMessage(error: ApiError, fallback: string): string {
  if (typeof error.detail === "string") return error.detail;
  if (Array.isArray(error.detail)) {
    return error.detail.map((item) => item.msg).filter(Boolean).join(" ") || fallback;
  }
  return fallback;
}

export async function apiRequest<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    credentials: "include",
    headers: {
      Accept: "application/json",
      ...(options?.body ? { "Content-Type": "application/json" } : {}),
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error = (await response.json().catch(() => ({}))) as ApiError;
    throw new ApiRequestError(
      errorMessage(error, `Request failed (${response.status})`),
      response.status,
    );
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export async function fetchMarketSummary(
  symbol: string,
  signal?: AbortSignal,
): Promise<MarketSummary> {
  const query = new URLSearchParams({ symbol });
  return apiRequest<MarketSummary>(`/api/v1/market-summary?${query}`, { signal });
}

export async function fetchMarketHistory(
  symbol: string,
  range: MarketRange,
  signal?: AbortSignal,
): Promise<MarketHistory> {
  const query = new URLSearchParams({ symbol, range });
  return apiRequest<MarketHistory>(`/api/v1/market-history?${query}`, { signal });
}
