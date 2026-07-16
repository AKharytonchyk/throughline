# Client Behavior Contract: Token-Usage Lens

How `app.js` consumes the `token_flow` blob section and renders the token lens. Mirrors feature 002's client model (analysis runs once in Python; the browser only filters + sums + renders). Traces to FR-### / SC-### in spec 003.

## Lens switch (FR-001, SC-005)

- A view-layer control switches between **Context window (chars)** — the existing occupancy views — and **Token usage** — the new views. Default lens: **Context window** (unchanged from today).
- The two lenses read **separate blob sections** (`cube`/`session_facts` vs `token_flow`) and **separate aggregation functions**. There is **no shared totals object and no unit conversion**. Switching only shows/hides sections.
- Both lenses share the **same filter bar** (repo + time range) and the **same intervention markers**. Changing the filter re-aggregates whichever lens is visible.

## Aggregation (pure, node-testable — dev only)

Exported pure functions over `token_flow`, filtered by the shared `filter` (project + `from`/`to` day range). These mirror 002's exported aggregators and get their own `node --test` file.

- `flowTotals(blob, filter)` → summed `{input, output, cache_write, cache_read, total, cache_read_share}` over sessions whose project/day pass the filter. **Units: tokens only.**
- `flowByModel(blob, filter)` → `modelId -> FlowTotals`, summed over filtered sessions; the union MUST reconcile to `flowTotals` (FR-009).
- `flowByDay(blob, filter)` → per-bucket `{bucket, input, output, cache_write, cache_read, total}` using the same day/week granularity chooser as 002; drives the over-time trend.
- `sessionGrowth(blob, sessionId)` → the session's downsampled cumulative series for the growth curve.
- `costEstimate(blob)` → present only when `blob.token_flow.cost.available`; returns per-model labeled figures; unpriced models flagged. Absent ⇒ no dollar output at all.

## Views

1. **Token flow by type (US1 / FR-002, FR-005)** — the four types with the **cache-read share** called out; per the filtered aggregate, plus a per-session table. Labeled **exact**. Reuses the occupancy lens's bar/row visual style but its own (tokens) data + scale.
2. **Re-billing growth (US2 / FR-006)** — for a selected session, the cumulative curve from `sessionGrowth`, cache-read emphasized. Inline SVG in the 002 chart style.
3. **Over-time trend (US3 / FR-007, FR-008)** — `flowByDay` rendered via the reused `lineChart`, honoring the filter and drawing intervention markers.
4. **By-model (FR-009)** — filtered per-model totals; reconciles to the overall total.
5. **Cost (US4 / FR-010)** — shown only when a price list is loaded; every figure carries an **estimate** label with the price basis (`effective` + unit); unpriced models shown as "unpriced," never guessed. Hidden entirely when no price list.

## Labels & honesty (SC-004, FR-004, FR-011)

- Every token figure is labeled **exact**; every cost figure is labeled **estimate** with its method.
- No **per-tool** token figure is presented as exact anywhere. If any per-tool token approximation is ever shown, it carries an estimate label and its method (e.g., "proportional by char share"). The default views do not show per-tool tokens.

## Coverage (D2)

- If `coverage.sessions_no_usage > 0`, the lens states how many sessions lacked usage data (partial coverage) rather than implying the totals are complete.

## Empty / edge states

- No token data in the filtered window → an explicit empty state (not a blank chart).
- `total == 0` → cache-read share renders as 0%, not NaN.
- Very large totals → human-scaled units (k / M / B).
