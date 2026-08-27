import type { Metadata } from "next";

import { UserSettings } from "@/components/settings/user-settings";

export const metadata: Metadata = {
  title: "Account settings | StockAI",
};

export default function SettingsPage() {
  return <UserSettings />;
}
