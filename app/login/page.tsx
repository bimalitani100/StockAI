import type { Metadata } from "next";
import Link from "next/link";

import { LoginForm } from "@/components/auth/login-form";

export const metadata: Metadata = {
  title: "Sign in | StockAI",
};

export default function LoginPage() {
  return (
    <main className="auth-page">
      <Link className="auth-brand" href="/">StockAI</Link>
      <LoginForm />
    </main>
  );
}
