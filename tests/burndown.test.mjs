// Dev-only unit test for app.js's PURE burn-down/levers aggregator (feature 005).
// Run: node --test tests/burndown.test.mjs   (built-in node:assert; no packages)
import { test } from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const API = require("../src/throughline/report/app.js");

// Hand-built blob: 1 repo, 4 days; a used tool (jira/search) + used Read, an UNUSED mounted
// tool (browser/open), one recurring chain (2 occ), one long session (200 turns) + one short.
function makeBlob() {
  return {
    dims: {
      projects: ["orbit/web"],
      days: ["2026-07-10", "2026-07-11", "2026-07-12", "2026-07-13"],
      tools: [
        { key: "mcp:jira/search", kind: "mcp_tool", server: "jira", tool: "search" },
        { key: "builtin:Read", kind: "builtin", server: null, tool: "Read" },
      ],
      modes: ["plan", "auto", "acceptEdits", "default", "unknown"],
    },
    mounted_keys: ["mcp:browser/open", "mcp:jira/search", "builtin:Read"], // browser/open unused
    mounted_resident: [
      { key: "mcp:browser/open", resident_tokens_est: 500, is_estimate: true, method: "m" },
      { key: "mcp:jira/search", resident_tokens_est: 300, is_estimate: true, method: "m" },
      { key: "builtin:Read", resident_tokens_est: 50, is_estimate: true, method: "m" },
    ],
    chars_per_token: 4,
    cube: [
      { p: 0, d: 0, t: 0, m: 1, sess: 0, n: 3, s: 900 }, // jira/search used on day 0
      { p: 0, d: 0, t: 1, m: 1, sess: 0, n: 5, s: 500 }, // Read used on day 0
    ],
    session_facts: [{ p: 0, d: 0, sess: 0, resident_est: 1000, non_tool: 200, sidechain_size: 0, sidechain_calls: 0 }],
    survival: { available: false, by_tool: {} },
    min_recurrence: 2,
    chain_shapes: [{
      chain_id: "c1",
      steps: [{ signature: "mcp:jira/search", fanout: false }, { signature: "builtin:Read", fanout: false }],
      proposal: { suggested_name: "jira_search_read", inputs: ["q"], output: "Read result" },
    }],
    chain_occurrences: [
      { chain_id: "c1", p: 0, d: 0, sess: 0, total_cost: 400, intermediate: 300 },
      { chain_id: "c1", p: 0, d: 1, sess: 0, total_cost: 400, intermediate: 300 },
    ],
    token_flow: {
      unit: "tokens",
      sessions: [
        { session: "long", p: 0, d: 0, turns: 200, no_usage: false,
          totals: { input: 1000, output: 500, cache_write: 2000, cache_read: 900000 },
          by_model: { opus: { input: 1000, output: 500, cache_write: 2000, cache_read: 900000 } },
          growth: [{ i: 0, cum_input: 5, cum_output: 2, cum_write: 100, cum_read: 1000 },
                   { i: 150, cum_input: 800, cum_output: 400, cum_write: 1800, cum_read: 600000 },
                   { i: 199, cum_input: 1000, cum_output: 500, cum_write: 2000, cum_read: 900000 }] },
        { session: "short", p: 0, d: 1, turns: 10, no_usage: false,
          totals: { input: 100, output: 50, cache_write: 200, cache_read: 5000 },
          by_model: { opus: { input: 100, output: 50, cache_write: 200, cache_read: 5000 } }, growth: [] },
      ],
      by_day: [
        { p: 0, d: 0, input: 1000, output: 500, cache_write: 2000, cache_read: 900000 },
        { p: 0, d: 1, input: 100, output: 50, cache_write: 200, cache_read: 5000 },
      ],
      models: ["opus"],
      coverage: { sessions_total: 2, sessions_no_usage: 0 },
    },
  };
}
const ALL = { project: null, from: null, to: null };

test("basis: active days + turns/day, small-sample flag (US3/D3)", () => {
  const b = API.leverBasis(makeBlob(), ALL);
  assert.equal(b.active_days, 2);          // days 0 and 1 have activity
  assert.equal(b.turns, 210);              // 200 + 10
  assert.equal(b.turns_per_day, 105);
  assert.equal(b.small_sample, true);      // 2 < 3
});

test("levers rank by tokens/day desc; session > unmount; chain dropped by floor (US1/SC-004/D9)", () => {
  const s = API.aggregateLevers(makeBlob(), ALL);
  assert.equal(s.empty_reason, null);
  // absolute floor = 1000 tok/day → chain (75/day) dropped; session (150000) + unmount (52500) kept
  const types = s.levers.map((l) => l.type);
  assert.deepEqual(types, ["session_length", "unmount"]);
  assert.equal(s.levers[0].tokens_per_day > s.levers[1].tokens_per_day, true); // descending (SC-004)
  // unmount browser/open = 500 * 105 turns/day
  const um = s.levers.find((l) => l.type === "unmount");
  assert.equal(um.id, "mcp:browser/open");
  assert.equal(um.tokens_per_day, 52500);
  // session lever = (900000 - 600000 at turn 150) / 2 active days = 150000
  assert.equal(s.levers[0].tokens_per_day, 150000);
});

test("every lever carries a non-empty method (SC-002)", () => {
  const s = API.aggregateLevers(makeBlob(), ALL);
  assert.ok(s.levers.length > 0);
  s.levers.forEach((l) => { assert.equal(typeof l.method, "string"); assert.ok(l.method.length > 0); });
});

test("no dollars without unit_prices; tokens still present (SC-003)", () => {
  const s = API.aggregateLevers(makeBlob(), ALL);
  assert.equal(s.priced, false);
  assert.equal(s.aggregate_dollars_per_day, null);
  s.levers.forEach((l) => assert.equal(l.dollars_per_day, null));
  assert.ok(s.aggregate_tokens_per_day > 0);
});

test("opt-in dollars: priced scope yields $/day; unpriced model excluded (US2/SC-003/D6)", () => {
  const blob = makeBlob();
  // add an unpriced second model on the long session
  blob.token_flow.sessions[0].by_model.mystery = { input: 0, output: 0, cache_write: 0, cache_read: 40000 };
  blob.token_flow.unit_prices = { available: true, currency: "USD", effective: "2026-07-01",
    unit_label: "USD per million tokens", per_million: true, by_model: { opus: { cache_read: 3.0 } } };
  const s = API.aggregateLevers(blob, ALL);
  assert.equal(s.priced, true);
  assert.deepEqual(s.unpriced_models, ["mystery"]);      // present in scope, no price → excluded, not guessed
  // blended cache-read price = 3.0 / 1e6 (only opus counted); session lever 150000 tok/day → $0.45/day
  const sess = s.levers.find((l) => l.type === "session_length");
  assert.ok(Math.abs(sess.dollars_per_day - 150000 * 3.0 / 1e6) < 1e-9);
  assert.ok(s.aggregate_dollars_per_day > 0);
});

test("aggregate = sum of shown levers, always non-additive caveat (US4/SC-006/D10)", () => {
  const s = API.aggregateLevers(makeBlob(), ALL);
  const sum = s.levers.reduce((a, l) => a + l.tokens_per_day, 0);
  assert.equal(s.aggregate_tokens_per_day, sum);
  assert.equal(s.overlap_caveat, true);
});

test("scope-aware recompute: date filter changes basis + lever set (US3)", () => {
  const late = API.aggregateLevers(makeBlob(), { project: null, from: "2026-07-11", to: null });
  assert.equal(late.basis.active_days, 1);   // only day 1 remains
  assert.equal(late.basis.small_sample, true);
  // day-0 cube cells drop out → all mounted tools now unused in-scope; long session excluded
  assert.ok(late.levers.some((l) => l.id === "mcp:jira/search"));
  assert.ok(!late.levers.some((l) => l.type === "session_length"));
});

test("empty scope → explicit empty_reason, no fabricated levers (SC-005/FR-009)", () => {
  const none = API.aggregateLevers(makeBlob(), { project: null, from: "2026-07-13", to: null });
  assert.equal(none.levers.length, 0);
  assert.ok(none.empty_reason && none.empty_reason.length > 0);
});
