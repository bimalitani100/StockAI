import type { Metadata } from "next";

import { AuthenticatedMarketWorkspace } from "@/components/market/authenticated-market-workspace";

export const metadata: Metadata = {
  title: "Market search | StockAI",
};

type MarketPageProps = {
  searchParams: Promise<{ symbol?: string | string[] }>;
};

export default async function MarketPage({ searchParams }: MarketPageProps) {
  const parameters = await searchParams;
  const requestedSymbol = Array.isArray(parameters.symbol) ? parameters.symbol[0] : parameters.symbol;
  return <AuthenticatedMarketWorkspace initialSymbol={requestedSymbol} />;
}
