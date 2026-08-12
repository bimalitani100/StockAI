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
  assert.match(html, /Frontend meets API/);
  assert.match(html, /GET \/api\/v1\/market-summary/);
  assert.doesNotMatch(html, /codex-preview|react-loading-skeleton|vinext/);
});
