# Phase 1 Data Model: Token Usage & Cost

The **flow** model (tokens) is deliberately separate from the **occupancy** model (chars, features 001/002). Types below are advisory; validation traces to FR-### / SC-### in spec 003. The Python side builds a compact `token_flow` blob section; the client re-aggregates it under the shared filter.

---

## TurnUsage (parser, per assistant turn)

Captured while parsing each session (extends `ParsedSession` in `parser/transcript.py`). Main-thread turns only (research D2).

| Field | Type | Notes |
|-------|------|-------|
| `input` | int | `usage.input_tokens` (missing ⇒ 0) |
| `output` | int | `usage.output_tokens` (missing ⇒ 0) |
| `cache_write` | int | `usage.cache_creation_input_tokens` (missing ⇒ 0) |
| `cache_read` | int | `usage.cache_read_input_tokens` (missing ⇒ 0) |
| `model` | str | `message.model` (e.g. `claude-opus-4-8`); `"unknown"` if absent |
| `ts` | str? | record `timestamp` (for day bucketing) |

A turn with **no `usage` block** contributes no TurnUsage and increments the session's `no_usage_turns`. All four counts are **exact reads** (FR-004); nothing here is derived.

---

## FlowTotals (value object)

| Field | Type |
|-------|------|
| `input`, `output`, `cache_write`, `cache_read` | int |

`total = input + output + cache_write + cache_read` (raw, unweighted — research D1). `cache_read_share = cache_read / total` (FR-005; 0 when total is 0).

---

## SessionTokenFlow (analysis/tokens.py, per session)

| Field | Type | Notes |
|-------|------|-------|
| `session` | str | session id |
| `project` | str | reused from the session's project (occupancy already derives it) |
| `turns` | int | count of turns with usage |
| `no_usage` | bool | true if the session had assistant turns but none carried usage (flagged, not dropped — D2) |
| `totals` | FlowTotals | the four exact sums |
| `by_model` | map<str, FlowTotals> | per-model split; MUST sum back to `totals` (FR-009, golden D8) |
| `growth` | list[GrowthPoint] | downsampled cumulative series, ≤120 points (D4) |

**Rule (SC-002)**: `totals` MUST equal the sum of the session's `TurnUsage`, zero discrepancy; `Σ by_model == totals`.

---

## GrowthPoint (downsampled cumulative, per session — D4)

| Field | Type | Notes |
|-------|------|-------|
| `i` | int | turn index at this sample (first and last always included) |
| `cum_input`, `cum_output`, `cum_write`, `cum_read` | int | cumulative totals up to turn `i` |

Even sampling across turn index, capped at 120 points; renders as the per-session re-billing curve.

---

## DayBucket (over-time trend — US3 / D5)

Turns bucketed by their own `ts` day.

| Field | Type | Notes |
|-------|------|-------|
| `p` | int | project index (into shared `dims.projects`) |
| `d` | int | day index (into shared `dims.days`) |
| `input`, `output`, `cache_write`, `cache_read` | int | per (project, day) token totals |

The client filters by `p` and `d`-range, chooses day/week granularity, and plots the trend with intervention markers (reused from 002).

---

## PriceList (config — `prices.json`, US4 / D7)

User-editable, **empty by default**. Schema: `contracts/price-list.schema.json`.

| Field | Type | Notes |
|-------|------|-------|
| `effective` | str? | date the prices are valid as-of (shown in the estimate label) |
| `models` | map<modelId, ModelPrice> | per-model unit prices |

**ModelPrice**: `{ input, output, cache_write, cache_read }` — price per token (or per million; the unit is stated in the schema and echoed in the label). Any field omitted ⇒ that type is treated as unpriced for that model.

---

## CostEstimate (analysis/cost.py — derived, labeled)

Produced only when `prices.json` is non-empty. For each (model, type) with a price: `cost = tokens × unit_price`. Models present in the data but absent from the price list are reported as **unpriced** (cost omitted + labeled), never guessed. Every figure carries an **estimate** label and the price basis (`effective` date + unit). The token lens renders fully with this entity absent.

---

## EmbeddedData additions (the blob — analysis → client contract)

A **new top-level `token_flow`** object is added to the existing embedded blob (schema: `contracts/embedded-token-flow.schema.json`). It does **not** modify or merge with `cube`, `session_facts`, or any occupancy totals. It reuses only the existing `dims.projects` / `dims.days` index tables.

| Field | Type |
|-------|------|
| `unit` | const `"tokens"` (distinct from the occupancy `"chars"`/`"bytes"`) |
| `sessions` | list[SessionTokenFlow] |
| `by_day` | list[DayBucket] |
| `models` | list[str] (model ids seen) |
| `coverage` | object `{ sessions_total, sessions_no_usage }` (surfaces the D2 flag) |
| `cost` | object? `{ available: bool, effective?: str, unit_label?: str, by_model: map<modelId,{priced:bool, ...}> }` — present only when a non-empty price list was loaded |

---

## Relationships

```text
ParsedSession* (001) ──parse usage──> TurnUsage*        (per main-thread turn)
TurnUsage* ──sum per session──> SessionTokenFlow*       (totals, by_model, growth)
TurnUsage* ──bucket by ts day──> DayBucket*             (over-time trend)
prices.json ──> PriceList ──cost.py──> CostEstimate     (optional, labeled)
  → token_flow (separate blob section) ──inlined──> app.js ──filter+aggregate+render──> token views
occupancy model (cube/session_facts, chars) ── stays separate; shares only dims + filter + markers ──┘
```
