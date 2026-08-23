import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

test("production build contains the StockAI foundation", async () => {
  const html = await readFile(
    new URL("../.next/server/app/index.html", import.meta.url),
    "utf8",
  );

  assert.match(html, /<title>StockAI/);
  assert.match(html, /Market intelligence/);
  assert.match(html, /Search a stock/);
  assert.match(html, /AUTO-UPDATING MARKET RESEARCH/);
  assert.match(html, /Requesting NVDA market data/);
  assert.doesNotMatch(html, /codex-preview|react-loading-skeleton|vinext/);
});

test("production build includes v0.7 account and role workspaces", async () => {
  const [login, register, dashboard, admin] = await Promise.all([
    readFile(new URL("../.next/server/app/login.html", import.meta.url), "utf8"),
    readFile(new URL("../.next/server/app/register.html", import.meta.url), "utf8"),
    readFile(new URL("../.next/server/app/dashboard.html", import.meta.url), "utf8"),
    readFile(new URL("../.next/server/app/admin.html", import.meta.url), "utf8"),
  ]);

  assert.match(login, /Sign in \| StockAI/);
  assert.match(login, /Welcome back/);
  assert.match(register, /Create account \| StockAI/);
  assert.match(dashboard, /Portfolio performance \| StockAI/);
  assert.match(admin, /Administration \| StockAI/);
});
