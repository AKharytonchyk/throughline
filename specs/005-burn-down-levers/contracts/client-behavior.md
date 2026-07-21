# Client Behavior Contract: Burn-Down / Levers

How `app.js` computes and renders the burn-down view from the embedded blob. Mirrors the
features 002/003 model (analysis runs once in Python; the browser only filters + composes +
renders). Traces to FR-### / SC-### in [spec.md](../spec.md). Blob additions:
[embedded-levers.schema.json](./embedded-levers.schema.json).

## Placement (D8, FR-013)

- Burn-down is the **first section of the Token-usage lens** (`#token-views`), labeled
  `01 — Biggest levers`. Existing token sections shift their display index to `02..05`.
- It is reachable via the existing lens switch; the occupancy lens's "Mounted but unused" line
  gains a one-line pointer to it. No new command, process, or asset.

## Aggregation (pure, node-testable — dev only)

New exported pure function, added to the `API` export alongside the existing aggregators so it
gets its own `node --test` file (`tests/burndown.test.mjs`).

`aggregateLevers(blob, filter)` → `BurndownSummary` (see [data-model.md](../data-model.md)).

It composes existing filtered signals — it does **not** re-implement them:

1. **Basis (D3)**: from the filtered `token_flow` sessions/`by_day`, compute
   `active_days` (distinct days with token activity) and `turns_per_day = Σ turns / active_days`.
   Flag `small_sample` when `active_days < 3`.
2. **Unmount levers (D2)**: for each key in `aggregateBreakdown(blob, filter).unused` that has a
   `mounted_resident` row, `tokens_per_day = resident_tokens_est × turns_per_day`. One lever per
   unused tool.
3. **Chain levers (D4)**: for each chain from `aggregateChains(blob, filter)`,
   `tokens_per_day = est_saved × recurrence / blob.chars_per_token / active_days`.
4. **Session-length lever (D5)**: over filtered `token_flow` sessions with `turns > threshold`,
   estimate post-threshold `cache_read` from each session's `growth` (`cum_read`), sum, divide by
   `active_days`. One aggregate lever.
5. **Dollarize (D6)**: when `token_flow.unit_prices.available`, compute the scope-blended
   `cache_read` unit price from `flowByModel(blob, filter)` × per-model prices (unpriced models
   excluded → `unpriced_models`), and set each lever's `dollars_per_day`. Otherwise `null`.
6. **Rank + floor (D9)**: drop levers below the stated significance floor; sort by
   `tokens_per_day` desc. If none survive, set `empty_reason`.
7. **Aggregate (D10)**: sum shown levers' `tokens_per_day` (and `$/day`); always carry the
   overlap/non-additive caveat.

Determinism: same `(blob, filter)` ⇒ identical `BurndownSummary` (no time/random inputs).

## Rendering (`renderBurndown`, wired into `renderTokens`)

- **US1** — a ranked list: each lever shows its `title`, `action`, `tokens_per_day` (human-scaled
  k/M/B), an `est` chip, and its `method` on hover (dotted-underline pattern from feature 004).
  The top row is the largest saving (SC-004). A long unmount list caps to top N with a "+K more".
- **US2** — when priced, each lever and the aggregate also show `$/day` with the price basis
  (`effective` + `unit_label`); unpriced-in-scope models are named as excluded. When
  `unit_prices` is absent, **no `$` renders anywhere**; token savings still render (SC-003).
- **US3** — the whole section recomputes on any filter change (it reads `filter`), like every
  other view; the basis line states `active_days` / `turns_per_day` and shows the small-sample
  note when flagged.
- **US4** — an aggregate "if you act on these" figure at the top of the section, rendered with
  the explicit non-additive/overlap caveat (SC-006).
- **Empty (FR-009/SC-005)** — when `empty_reason` is set, render an explicit "no significant
  levers found in this window" message; never a fabricated or zero-value row.

## Labels & honesty (Principle V, FR-003/FR-006/FR-010/FR-014)

- Every projected figure carries an **estimate** chip and a stated **method**; nothing is shown
  as exact.
- The view is **advisory**: it describes the change; it renders **no** control that installs or
  enforces caps or otherwise acts on Claude Code (FR-010).
- Dollar figures obey feature 003's rule: opt-in, empty by default, unpriced never guessed.

## Edge states

- No unused tools / no chains / no long sessions in scope → `empty_reason` set (explicit state).
- `active_days == 0` (no token activity in scope) → empty state, never divide-by-zero.
- Resident/chain figures are estimates built on estimates → method text states the provenance;
  never relabeled exact.
- Very large savings → human-scaled units (k / M / B).
