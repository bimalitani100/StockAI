export type MarketRange = "1d" | "1w" | "1m" | "3m" | "ytd" | "1y" | "5y" | "max";

export interface MarketSummary {
  symbol: string;
  company_name: string;
  price: number;
  currency: string;
  previous_close: number;
  change: number;
  change_percent: number;
  market_state: string;
  as_of: string;
  source: string;
  is_realtime: boolean;
  refresh_seconds: number;
}

export interface MarketHistoryPoint {
  timestamp: string;
  price: number;
}

export interface MarketHistory {
  symbol: string;
  company_name: string;
  currency: string;
  range: MarketRange;
  interval: string;
  price: number;
  baseline_price: number;
  change: number;
  change_percent: number;
  market_state: string;
  as_of: string;
  points: MarketHistoryPoint[];
  source: string;
  is_realtime: boolean;
  refresh_seconds: number;
}
