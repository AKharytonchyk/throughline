# Research: Burn-Down / Biggest Levers

Phase 0. Resolves the unknowns behind the space→flow conversion, the per-day basis, and the
two blob additions. Format: Decision / Rationale / Alternatives.

## D1 — Levers are computed client-side, not in Python

**Decision**: Add a pure `aggregateLevers(blob, filter)` in `app.js`; Python embeds only the
raw facts. No lever is precomputed server-side.

**Rationale**: Features 002/003 established that analysis runs **once** in Python and the
browser re-aggregates on every filter change. US3 requires levers (and their per-day savings)
to recompute instantly when the repo/time filter changes. The existing filtered signals
(`aggregateBreakdown().unused`, `aggregateChains()`, `token_flow` sessions) are already
client-side; composing them there is the only way to stay live without a re-run.

**Alternatives**: Precompute levers per (project, day) in Python — rejected: it duplicates the
filtering logic that already lives in the client and cannot honor arbitrary date windows.

## D2 — Unmount lever: space→flow conversion

**Decision**: For a tool that is **mounted but unused in the filtered scope**, projected
saving = `resident_tokens_est(tool) × turns_per_day`, where `resident_tokens_est(tool)` is the
tool's estimated schema size (see D7) and `turns_per_day` is from D3.

**Rationale**: A mounted tool's schema is resident in the window and re-sent as `cache_read`
on **every turn** (feature 003's core finding: bill ≈ resident × turns). Unmounting it removes
that per-turn cost. This is the cleanest, most defensible bridge from the space signal (schema
chars) to the flow unit (tokens/day). Labeled an estimate; inherits `sizing.RESIDENT_METHOD`.

**Alternatives**: Count the schema once (space lens) — rejected: it under-weights the true
cost, which is the whole point of the token lens. Use exact per-turn cache_read attributable to
the tool — impossible: `usage` is per turn, not per tool (feature 003 FR-011).

## D3 — Per-day basis = active days, turns_per_day

**Decision**: `active_days` = count of distinct days **with token activity** in the filtered
scope — the distinct days present in `token_flow.by_day` after filtering, i.e. the same source
`flowByDay` already uses. `turns_per_day = Σ turns / active_days`. Both are stated in the
output; a **small-sample flag** is shown when `active_days < 3`.

**Rationale**: Averaging over active days (not calendar days) keeps idle weekends from
deflating the rate, matching how a user reasons about "a working day." Turns/day is the
multiplier that turns a per-turn resident cost into a daily cost. Using tokens already in the
scope keeps it internally consistent with the token lens.

**Alternatives**: Calendar-day average — rejected: understates the daily rate for bursty
usage. A fixed "turns per day" constant — rejected: not defensible, varies per user.

## D4 — Chain lever conversion

**Decision**: For each recurring collapsible chain in scope, projected saving (tokens/day) =
`(est_saved_chars_per_occurrence × recurrence_in_scope) / chars_per_token / active_days`.
Labeled an estimate; the method line notes it is **collapsible round-trip content amortized per
day**, a *different mechanism* than resident re-billing (hence the non-additive aggregate, D10).

**Rationale**: `aggregateChains` already yields `est_saved` (avg intermediate chars a single
intent-tool would remove per occurrence) and `recurrence` for the filtered scope. Multiplying
gives total collapsible chars in scope; dividing by `chars_per_token` and `active_days` puts it
in the same tokens/day unit as the other levers so they can be ranked together.

**Alternatives**: Leave chains in chars (as today) — rejected: cannot be ranked against the
token-denominated unmount/session levers. Re-bill the chain content × turns like resident —
rejected: overstates it; collapsed content is not resident schema.

## D5 — Session-length (long-session) lever

**Decision**: One aggregate lever. Identify sessions in scope with `turns > LONG_SESSION_TURNS`
(a disclosed client constant = **150 turns**, stated in the advisory text; see D9). For each,
estimate `cache_read` accrued **after** the threshold turn by interpolating the session's
`growth` series (`cum_read` at the threshold turn vs final); sum across long sessions and divide
by `active_days`. Advisory text: "N sessions ran past T turns — clearing/compacting sooner would
save ≈ X/day." Labeled estimate with method.

**Rationale**: `growth` already carries downsampled cumulative `cum_read`, so the post-threshold
re-billing is estimable without new data. It captures the "long sessions re-pay resident context
every turn" cost the re-billing curve visualizes, expressed as a daily saving.

**Alternatives**: Per-session levers — rejected: noisy and clutters the ranked list; one
advisory aggregate is clearer. Use total cache_read of long sessions — rejected: overstates it
(early turns would be paid regardless); post-threshold excess is the honest figure.

## D6 — Dollarizing a scope-specific saving

**Decision**: Compute a **blended cache_read unit price** for the filtered scope:
`Σ_model (cache_read_tokens_in_scope[model] × price[model].cache_read) / Σ_model cache_read_tokens_in_scope[model]`,
using per-model unit prices embedded from `prices.json` (D7). Multiply each lever's tokens/day by
this blended price. Models with no price are **excluded** from the blend and the exclusion is
labeled. With no price list at all, **no `$` appears** and token savings still show.

**Rationale**: Savings are token-type quantities (dominated by cache_read), not tied to one
model. A scope-weighted blend keeps `$/day` consistent with the filtered token mix and recomputes
live. Reuses feature 003's opt-in, empty-by-default, never-guessed price contract.

**Alternatives**: Reuse the existing whole-dataset `cost` blob — rejected: it is not
scope-aware and exposes computed totals, not unit prices. Pick a single model's price —
rejected: arbitrary and wrong when multiple models are in scope.

## D7 — Two additive blob tables (built once in `aggregate.py`)

**Decision**:
1. `mounted_resident`: `[{key, resident_tokens_est}]` — one row per mounted tool, the estimated
   per-turn schema tokens (`sizing.resident_estimate().per_tool[key] / chars_per_token`,
   averaged over sessions where the tool is mounted). Carries `is_estimate: true` +
   `method` (= `RESIDENT_METHOD`).
2. `token_flow.unit_prices`: `{available, currency, effective, unit_label, per_million,
   by_model: {model: {input, output, cache_write, cache_read}}}` — the per-model unit prices
   from the parsed `prices.json`. Present only when a non-empty price list was loaded (mirrors
   the existing `cost` gate). Absent ⇒ no `$` anywhere.

A **golden reconciliation test** asserts `Σ mounted_resident.resident_tokens_est` (over a
session's mounted set) `× chars_per_token + system_prompt_size ≈ resident_est` for that session
(within rounding), so the split is trustworthy — the same discipline feature 002 used for the
cube.

**Rationale**: These are the only two facts the client lacks. Both are filter-independent
(schema size and unit prices don't depend on the window), so they belong in the embedded blob,
not recomputed per filter. Both are small (O(mounted tools), O(priced models)).

**Alternatives**: Embed per-(session, tool) resident — rejected: larger and unnecessary; a
representative per-tool figure suffices for a labeled estimate. Embed computed lever dollars —
rejected: not scope-aware (D6). `chars_per_token` is also embedded (currently only in `Config`)
so the client can convert chars↔tokens.

## D8 — Placement: lead section of the Token-usage lens

**Decision**: Render burn-down as the **first section of the token lens** (`#token-views`),
labeled `01 — Biggest levers`; the existing token sections shift to `02..05` (display index
strings only). The occupancy lens's "Mounted but unused" line gains a one-line pointer to it.

**Rationale**: Lever outputs are in the flow unit (tokens/day, `$/day`), which is the token
lens's unit; putting it there keeps units coherent (features insist the two lenses never share
units). It becomes the headline of the lens the "caps are coming" user opens to see cost.

**Alternatives**: A third lens or an always-visible top-of-page panel — rejected: more UI
surface and a shared-units risk for little gain (Simplicity First). Occupancy lens — rejected:
that lens is chars; lever savings are tokens/$.

## D9 — Lever granularity, threshold, and the significance floor

**Decision**:
- **Unmount**: one lever **per unused tool** (enables true ranking); the panel caps the visible
  list (e.g., top N) and rolls the remainder into a "+K more" line.
- **Chains**: one lever per chain shape (as `aggregateChains` already yields).
- **Session-length**: one aggregate lever (D5).
- **Threshold** for "long" sessions: a disclosed client constant `LONG_SESSION_TURNS = 150`
  (a JS constant in `app.js`, **not** a `Config` field — no unrequested configurability,
  Principle VIII); stated in the advisory text so it stays calibratable.
- **Significance floor**: drop any lever whose projected saving is **below 1,000 tokens/day**
  (negligible), and drop any zero or negative saving. An **absolute** floor is used rather than a
  percentage of scope cache-read: when one mechanism dominates (e.g. a 9M-tokens/day
  session-length lever), a relative floor hides every other genuinely useful lever (a 10k/day
  unmount), defeating the ranked-list purpose. The absolute floor drops only true noise and lets
  ranking + the top-N display cap manage clutter. When **no** lever clears the floor, show the
  explicit "no significant levers found" state (FR-009, SC-005). The floor is stated in the output.
- **Unmount display cap**: show the top **8** unmount levers, rolling the rest into a "+K more"
  line (ranking still uses all of them).

**Rationale**: Per-tool unmount levers rank honestly; a floor prevents a wall of trivial rows
and satisfies the "don't fabricate" requirement. All thresholds are stated so the estimate stays
calibratable (Principle V).

**Alternatives**: Group all unused tools into one lever — rejected: loses ranking granularity
the spec's "sorted by impact" implies (kept as a fallback display when the list is long).

## D10 — Aggregate is explicitly non-additive

**Decision**: The aggregate "if you act on these" figure sums the shown levers' tokens/day (and
`$/day`) but is rendered **with an explicit caveat** that per-lever savings can overlap (e.g., a
chain that also involves a rarely-used tool) and are **not guaranteed to sum exactly**.

**Rationale**: Different mechanisms (resident re-billing vs collapsed round-trips vs session
length) can touch overlapping spend; presenting a naive sum as exact would violate Principle V.
The caveat is the honest framing (FR-007, SC-006).

**Alternatives**: Compute an overlap-corrected total — rejected: not reliably attributable from
per-turn data and would itself be a shakier estimate than the disclosed caveat.

## Open questions

None. All resolved above; thresholds/floors (D9) are stated-in-output constants, not blocking
unknowns.
