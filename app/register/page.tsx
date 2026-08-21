import type { Metadata } from "next";
import Link from "next/link";

import { RegisterForm } from "@/components/auth/register-form";

export const metadata: Metadata = {
  title: "Create account | StockAI",
};

export default function RegisterPage() {
  return (
    <main className="auth-page">
      <Link className="auth-brand" href="/">StockAI</Link>
      <RegisterForm />
    </main>
  );
}
