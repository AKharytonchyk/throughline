// Dev-only unit test for app.js's PURE aggregation functions (feature 002, T034).
// Run: node --test tests/app_aggregate.test.mjs   (built-in node:assert; no packages)
// Not a tool runtime dependency — node is only needed for this test.
import { test } from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const API = require("../src/throughline/report/app.js");

// A tiny hand-built blob: 2 projects, 2 days, tools Read+Bash, modes auto+plan.
// tools idx: 0 builtin:Read, 1 builtin:Bash
const blob = {
  unit: "chars",
  dims: {
    projects: ["projA", "projB"],
    days: ["2026-07-01", "2026-07-08"],
    tools: [
      { key: "builtin:Read", kind: "builtin" },
      { key: "builtin:Bash", kind: "builtin" },
    ],
    modes: ["plan", "auto", "acceptEdits", "default", "unknown"],
  },
  mounted_keys: ["builtin:Read", "builtin:Bash", "builtin:Grep"],
  // cube: [p,d,t,m,sess,n,s]
  cube: [
    { p: 0, d: 0, t: 0, m: 1, sess: 0, n: 2, s: 2000 },  // projA, 07-01, Read, auto: 2 calls, avg 1000
    { p: 0, d: 1, t: 0, m: 0, sess: 1, n: 4, s: 1200 },  // projA, 07-08, Read, plan: 4 calls, avg 300
    { p: 1, d: 0, t: 1, m: 1, sess: 2, n: 1, s: 500 },   // projB, 07-01, Bash, auto
  ],
  session_facts: [
    { p: 0, d: 0, sess: 0, resident_est: 400, non_tool: 100, sidechain_size: 0, sidechain_calls: 0 },
    { p: 0, d: 1, sess: 1, resident_est: 400, non_tool: 50, sidechain_size: 0, sidechain_calls: 0 },
    { p: 1, d: 0, sess: 2, resident_est: 200, non_tool: 20, sidechain_size: 30, sidechain_calls: 1 },
  ],
  chain_shapes: [{ chain_id: "c1", steps: [{ signature: "builtin:Read", fanout: false },
    { signature: "builtin:Bash", fanout: false }], proposal: { suggested_name: "Read_Bash", inputs: ["x"], output: "Bash result" } }],
  chain_occurrences: [
    { chain_id: "c1", p: 0, d: 0, sess: 0, total_cost: 900, intermediate: 600 },
    { chain_id: "c1", p: 1, d: 0, sess: 2, total_cost: 800, intermediate: 500 },
  ],
  survival: { available: false, by_tool: {} },
  compaction: { events: 0, pre_tokens: 0, post_tokens: 0, retention_pct: null, exact: true },
  interventions: [],
  min_recurrence: 2,
};

test("filter predicate: project + date range", () => {
  assert.equal(API.filterCells(blob, { project: null, from: null, to: null }).length, 3);
  assert.equal(API.filterCells(blob, { project: "projA", from: null, to: null }).length, 2);
  assert.equal(API.filterCells(blob, { project: null, from: "2026-07-08", to: null }).length, 1);
});

test("breakdown sums per tool + resident + non-tool + total", () => {
  const bd = API.aggregateBreakdown(blob, { project: null, from: null, to: null });
  const read = bd.rows.find((r) => r.key === "builtin:Read");
  assert.equal(read.size, 3200);        // 2000 + 1200
  assert.equal(read.calls, 6);
  // total = per-call (2000+1200+500) + resident (1000) + non_tool (170)
  assert.equal(bd.total, 3700 + 1000 + 170);
  assert.ok(bd.rows.some((r) => r.kind === "resident" && r.is_estimate));
  assert.deepEqual(bd.unused, ["builtin:Grep"]);  // mounted but never called
});

test("trend: avg-per-call falls while count rises (SC-004)", () => {
  const series = API.aggregateTrend(blob, { project: null, from: null, to: null }, "builtin:Read");
  const w1 = series.find((b) => b.bucket === "2026-07-01");
  const w2 = series.find((b) => b.bucket === "2026-07-08");
  assert.ok(w2.calls > w1.calls);                 // 4 > 2
  assert.ok(w2.avg_per_call < w1.avg_per_call);   // 300 < 1000
  assert.equal(w1.avg_per_call, 1000);
});

test("mode: per-call & per-session; auto cheaper-per-call not asserted, metrics present", () => {
  const segs = API.aggregateMode(blob, { project: null, from: null, to: null });
  const auto = segs.find((s) => s.mode === "auto");
  const plan = segs.find((s) => s.mode === "plan");
  assert.equal(auto.avg_per_call, 2500 / 3);      // (2000+500)/(2+1)
  assert.equal(plan.avg_per_call, 300);           // 1200/4
  assert.equal(plan.sessions, 1);
});

test("chains: recurrence >= min_recurrence kept; below is dropped when filtered", () => {
  const all = API.aggregateChains(blob, { project: null, from: null, to: null });
  assert.equal(all.length, 1);
  assert.equal(all[0].recurrence, 2);
  const projB = API.aggregateChains(blob, { project: "projB", from: null, to: null });
  assert.equal(projB.length, 0);                  // only 1 occurrence in projB < min_recurrence 2
});
