# Data Model: Burn-Down / Biggest Levers

Entities are split into (a) two **additive blob fields** built once in Python and (b) the
**client-derived** lever objects computed by `aggregateLevers(blob, filter)`. Nothing here is
persisted; the blob is embedded in `dashboard.html` exactly as today.

## Blob additions (Python → embedded, built once)

### `mounted_resident` (top-level array)

One row per mounted tool — the estimated **per-turn** resident (schema) token cost, used to
price an unmount lever.

| Field | Type | Notes |
|-------|------|-------|
| `key` | string | Tool key, matches `dims.tools[].key` and `mounted_keys` (`mcp:server/tool`, `builtin:Name`). |
| `resident_tokens_est` | number | Estimated per-turn resident tokens = `per_tool_chars / chars_per_token`, averaged over sessions where the tool is mounted. **Estimate.** |
| `is_estimate` | boolean | Always `true`. |
| `method` | string | `sizing.RESIDENT_METHOD` (the disclosed per-tool split heuristic). |

**Invariant (golden)**: for each session, `Σ per_tool_chars + system_prompt_size == resident_est`
(already true in `sizing`); the embedded `resident_tokens_est × chars_per_token` reconciles to
that per-tool share within rounding.

### `chars_per_token` (top-level number)

The disclosed chars↔tokens factor from `Config` (default 4.0). Newly embedded so the client can
convert chain chars (space) into tokens (flow). Labeled in method text wherever used.

### `token_flow.unit_prices` (object, optional)

Per-model unit prices from the parsed `prices.json`. Present **only** when a non-empty price
list was loaded (same gate as the existing `token_flow.cost`). Absent ⇒ no `$` anywhere.

| Field | Type | Notes |
|-------|------|-------|
| `available` | boolean | `true` when prices loaded. |
| `currency` | string | e.g. `USD`. |
| `effective` | string \| null | Price-basis date. |
| `unit_label` | string | e.g. `USD per million tokens`. |
| `per_million` | boolean | Whether prices are per-million or per-token. |
| `by_model` | object | `{ modelId: { input?, output?, cache_write?, cache_read? } }`; missing type ⇒ that type unpriced for that model. |

## Client-derived entities (computed in `aggregateLevers`, not embedded)

### `Lever`

| Field | Type | Notes |
|-------|------|-------|
| `type` | enum | `"unmount"` \| `"chain"` \| `"session_length"`. |
| `id` | string | Tool key, chain_id, or `"session_length"`. |
| `title` | string | Short label (e.g., tool short-name, chain proposal name). |
| `action` | string | Plain-language advisory (what to unmount/collapse/shorten). **Never executed.** |
| `tokens_per_day` | number | Projected daily saving in tokens. **Estimate.** |
| `dollars_per_day` | number \| null | Projected daily `$` saving, or `null` when no/partial pricing. **Estimate.** |
| `method` | string | The conversion method for this lever (D2/D4/D5). |
| `basis` | object | `{ active_days, turns_per_day, small_sample: bool }` (D3). |

### `BurndownSummary`

| Field | Type | Notes |
|-------|------|-------|
| `levers` | Lever[] | Sorted by `tokens_per_day` desc; below-floor levers dropped (D9). |
| `aggregate_tokens_per_day` | number | Σ of shown levers' `tokens_per_day`. |
| `aggregate_dollars_per_day` | number \| null | Σ of shown levers' `dollars_per_day`, or `null`. |
| `overlap_caveat` | true | Always present — the aggregate is **not** guaranteed additive (D10). |
| `priced` | boolean | Whether any `$` figure is shown (from `unit_prices.available`). |
| `unpriced_models` | string[] | Models seen in scope but excluded from the `$` blend (labeled). |
| `empty_reason` | string \| null | Set when `levers` is empty (e.g., "no significant levers"), for the explicit empty state (FR-009). |

## Relationships & derivation

```text
mounted_resident[key].resident_tokens_est ─┐
aggregateBreakdown().unused (per filter) ──┼─► unmount Lever  (× turns_per_day)     (D2)
aggregateChains() est_saved + recurrence ──┼─► chain Lever    (/ chars_per_token/D) (D4)
token_flow sessions turns + growth.cum_read┼─► session Lever  (post-threshold /D)   (D5)
token_flow.by_day (active days, turns) ────┴─► basis {active_days, turns_per_day}    (D3)
token_flow.unit_prices + flowByModel ─────────► blended cache_read $/token → $/day   (D6)
```

## Validation rules

- Every `Lever.tokens_per_day` and `dollars_per_day` is an **estimate** and carries `method`
  (Principle V / FR-003, FR-014).
- `dollars_per_day` is `null` unless `unit_prices.available`; unpriced-in-scope models are
  excluded and surfaced in `unpriced_models` — never guessed (FR-006).
- `levers` sorted strictly by `tokens_per_day` desc; the top entry is the max (SC-004).
- Empty `levers` ⇒ `empty_reason` set and rendered as the explicit no-levers state (SC-005).
- `aggregate_*` always accompanied by `overlap_caveat` in the render (SC-006).
- All computation is client-side, offline, over embedded data; no network, no writes (FR-011/12).

## Disclosed constants (client-side, stated in output)

These are fixed JS constants in `app.js` (not `Config` fields — no unrequested configurability,
Principle VIII), each surfaced in the view so the estimate stays calibratable (Principle V):

| Constant | Value | Used by | Stated where |
|----------|-------|---------|--------------|
| `LONG_SESSION_TURNS` | 150 turns | session-length lever (D5) | the lever's advisory/method text |
| `LEVER_FLOOR_TPD` | 1,000 tokens/day (absolute; drop zero/negative) | ranking (D9) | the section (empty state when nothing clears it) |
| unmount display cap | top 8 (rest → "+K more") | render (D9) | the "+K more" line |
| small-sample flag | `active_days < 3` | basis (D3) | the basis line |
