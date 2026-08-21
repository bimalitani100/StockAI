import type { Metadata } from "next";

import { UserDashboard } from "@/components/dashboard/user-dashboard";

export const metadata: Metadata = {
  title: "Portfolio performance | StockAI",
};

export default function DashboardPage() {
  return <UserDashboard />;
}
