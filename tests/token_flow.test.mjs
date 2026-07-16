// Dev-only unit test for app.js's PURE token-flow aggregators (feature 003, T010/T020).
// Run: node --test tests/token_flow.test.mjs   (built-in node:assert; no packages)
// Not a tool runtime dependency — node is only needed for this test.
import { test } from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const API = require("../src/throughline/report/app.js");

// A tiny hand-built blob: 2 projects, 3 real days (+undated), 2 sessions, 2 models.
const blob = {
  dims: {
    projects: ["orbit/web", "orbit/api"],
    days: ["2026-07-10", "2026-07-11", "2026-07-12", "undated"],
  },
  token_flow: {
    unit: "tokens",
    sessions: [
      { session: "a", p: 0, d: 0, turns: 2, no_usage: false,
        totals: { input: 10, output: 5, cache_write: 20, cache_read: 100 },
        by_model: { opus: { input: 8, output: 5, cache_write: 20, cache_read: 80 },
                    haiku: { input: 2, output: 0, cache_write: 0, cache_read: 20 } },
        growth: [{ i: 0, cum_input: 5, cum_output: 2, cum_write: 10, cum_read: 50 },
                 { i: 1, cum_input: 10, cum_output: 5, cum_write: 20, cum_read: 100 }] },
      { session: "b", p: 1, d: 1, turns: 1, no_usage: false,
        totals: { input: 1, output: 1, cache_write: 0, cache_read: 8 },
        by_model: { opus: { input: 1, output: 1, cache_write: 0, cache_read: 8 } }, growth: [] },
    ],
    by_day: [
      { p: 0, d: 0, input: 10, output: 5, cache_write: 20, cache_read: 100 },
      { p: 1, d: 1, input: 1, output: 1, cache_write: 0, cache_read: 8 },
    ],
    models: ["opus", "haiku"],
    coverage: { sessions_total: 2, sessions_no_usage: 0 },
  },
};
const ALL = { project: null, from: null, to: null };

test("flowTotals sums the four types + cache-read share", () => {
  const t = API.flowTotals(blob, ALL);
  assert.equal(t.input, 11);
  assert.equal(t.output, 6);
  assert.equal(t.cache_write, 20);
  assert.equal(t.cache_read, 108);
  assert.equal(t.total, 145);
  assert.ok(Math.abs(t.cache_read_share - 108 / 145) < 1e-9);
});

test("flowByModel reconciles to flowTotals (FR-009)", () => {
  const t = API.flowTotals(blob, ALL);
  const bm = API.flowByModel(blob, ALL);
  const recon = Object.keys(bm).reduce((s, m) => s + bm[m].total, 0);
  assert.equal(recon, t.total);
  assert.equal(bm.opus.total, 9 + 6 + 20 + 88); // in 8+1, out 5+1, write 20, read 80+8 = 123
  assert.equal(bm.haiku.total, 22);             // in 2, out 0, write 0, read 20
});

test("cache_read_share is 0 (not NaN) when total is 0", () => {
  const empty = { ...blob, token_flow: { ...blob.token_flow, sessions: [] } };
  const t = API.flowTotals(empty, ALL);
  assert.equal(t.total, 0);
  assert.equal(t.cache_read_share, 0);
});

test("project filter restricts flowTotals/flowByModel to one repo", () => {
  const web = API.flowTotals(blob, { project: "orbit/web", from: null, to: null });
  assert.equal(web.total, 135); // session a only
  const bm = API.flowByModel(blob, { project: "orbit/api", from: null, to: null });
  assert.equal(Object.keys(bm).join(","), "opus"); // session b is opus-only
});

test("flowByDay buckets by day, honors filters, and reconciles", () => {
  const all = API.flowByDay(blob, ALL);
  assert.equal(all.length, 2);
  assert.equal(all.reduce((s, b) => s + b.total, 0), 145);
  // project filter → only orbit/api's single day bucket (10 tokens)
  const api = API.flowByDay(blob, { project: "orbit/api", from: null, to: null });
  assert.equal(api.length, 1);
  assert.equal(api[0].total, 10);
  // date-range filter → only 2026-07-11 onward (session b)
  const late = API.flowByDay(blob, { project: null, from: "2026-07-11", to: null });
  assert.equal(late.length, 1);
  assert.equal(late[0].bucket, "2026-07-11");
  assert.equal(late[0].total, 10);
});

test("sessionGrowth returns the session's downsampled series; costEstimate absent by default", () => {
  assert.equal(API.sessionGrowth(blob, "a").length, 2);
  assert.equal(API.sessionGrowth(blob, "missing").length, 0);
  assert.equal(API.costEstimate(blob), null);
});
