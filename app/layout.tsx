import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "StockAI — Market intelligence, built in the open",
  description: "A production-minded stock research platform built as a hands-on software engineering project.",
  icons: { icon: "/favicon.svg" },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en" data-scroll-behavior="smooth"><body>{children}</body></html>;
}
