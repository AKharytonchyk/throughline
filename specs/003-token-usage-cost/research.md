# Phase 0 Research: Token Usage & Cost

All decisions are grounded in read-only inspection of real transcripts under `~/.throughline/transcripts`. No `NEEDS CLARIFICATION` remain.

---

## D1 — Token fields: source of truth

**Decision**: Read the four types verbatim from each assistant turn's `message.usage`, mapped exactly:

| Lens term | `usage` field |
|-----------|---------------|
| input | `input_tokens` |
| output | `output_tokens` |
| cache-write | `cache_creation_input_tokens` |
| cache-read | `cache_read_input_tokens` |

Also read the model id from `message.model` and the turn time from the record-level `timestamp`. Counts are **read, not derived** — this is what makes the "exact" label (FR-004) truthful.

**Rationale**: Confirmed on a real transcript: an assistant record has `message.usage` with all four keys present (e.g. `input_tokens:6334, cache_creation_input_tokens:20405, cache_read_input_tokens:9116, output_tokens:297`) and `message.model:"claude-opus-4-8"`. The parser today reads only `cache_creation_input_tokens` (for the resident estimate, `transcript.py:155`); this feature reads the other three plus model.

**Alternatives considered**: Deriving tokens from char counts ÷ a factor — rejected; that is an estimate and would violate the "exact" promise. The existing `chars_per_token` factor stays confined to the resident *char* estimate in the occupancy lens.

---

## D2 — Which turns count; missing data

**Decision**: Count **main-thread assistant turns** that carry a `usage` block. Exclude `isSidechain` turns (consistent with the occupancy lens; sub-agent windows are feature 004). For a turn present but missing a field, that field counts as **0**. A turn or session with **no `usage` block at all** is **flagged** (a `no_usage` marker), not silently dropped.

**Rationale**: Keeps 003 strictly "main window," matching how the occupancy lens uses `main_thread_calls()`. Flagging rather than dropping preserves Correctness (V) — the user learns coverage is partial instead of seeing an understated total. Real data shows sidechain turns are ~absent for the new `Agent` tool anyway.

**Alternatives considered**: Include sidechain turns now — rejected; that pre-empts feature 004 and would mix separate windows.

---

## D3 — Lens separation (architectural boundary, FR-001)

**Decision**: The occupancy model (chars, per-tool: existing `cube` + `session_facts`) and the flow model (tokens, per-turn/per-session: new `token_flow`) are **separate top-level sections** of the embedded blob, built by separate code, aggregated by separate client functions, and rendered into separate view sections. A **view-layer lens switch** shows one or the other. The **only** shared surfaces are: the `dims` index tables (projects, days — index tables, not aggregates), the feature-002 `filter` object, and the intervention markers.

**Rationale**: Directly implements FR-001 and SC-005 — different units and granularity must never collapse into one model under a toggle. Sharing only index tables keeps the blob small without merging the two models.

**Alternatives considered**: A single unified aggregate with a `unit` flag — rejected; it would force chars and tokens (and per-tool vs per-turn granularity) into one shape, exactly what the spec forbids.

---

## D4 — Per-session growth curve (US2) representation *(left open by the user)*

**Decision**: Embed, per session, a **downsampled cumulative-tokens series capped at ≤ 120 points** (even sampling across turn index, always preserving the first and last turn), split by the four types so the curve can show cumulative cache-read vs the rest. Render it as an inline-SVG line/area chart reusing feature 002's chart style (`app.js` `lineChart` conventions). Downsampling happens once at generation time.

**Rationale**: Sessions reach ~10k turns; embedding every turn would bloat the single self-contained HTML and slow rendering, for no visual gain (120 points is more than a chart is wide in CSS px). ≤120 points keeps the blob tiny and the curve smooth. Reusing the existing SVG/vanilla-JS builder honors "reuse, don't rebuild" and needs no library.

**Alternatives considered**: (a) Full per-turn arrays — rejected (blob bloat). (b) Recompute client-side from embedded raw turns — rejected (would require embedding raw turns). (c) A fixed time-based bucketing within a session — rejected; turn index is the natural x-axis for "re-billing per turn."

---

## D5 — Over-time trend (US3) *(left open by the user)*

**Decision**: Bucket **turns by their own timestamp day**, then reuse `timeline.day_of` / `week_of` / `choose_granularity` / `bucket_of` (daily ≤14-day span, else weekly). Embed a compact `by_day` series of the four token totals per (project, day). Render via the reused `lineChart`, honoring the existing repo/time-range filters and drawing the existing intervention markers.

**Rationale**: Reuses 002's proven bucketing and chart, and 002's filter/marker machinery, so US3 is a thin new view rather than new infrastructure. Bucketing by each turn's own timestamp (not the session's) keeps a long, multi-day session correctly spread across days.

**Alternatives considered**: Attribute a whole session to its first day — rejected; loses accuracy for long sessions. Introduce new filtering — rejected; reuse 002's.

---

## D6 — By-model attribution (FR-009)

**Decision**: Aggregate token totals **per `message.model`** at the session grain (`by_model` inside each session's flow record); the client sums per-model across the filtered sessions. The full per-model split MUST reconcile to the session's recorded usage when a session spans multiple models.

**Rationale**: Pricing and behavior differ by model (real data shows `claude-opus-4-8`); per-model is needed both for cost (D7) and for honest reporting. Per-model reconciliation is folded into the golden test (D8).

**Alternatives considered**: Single blended model bucket — rejected; hides which model drove spend and breaks cost attribution.

---

## D7 — Dollar-cost estimate (US4 / FR-010), isolated & opt-in

**Decision**: A new `prices.json` in the working directory (loader in `config.py` mirroring `load_interventions`), **shipping empty**. `analysis/cost.py` multiplies per-model, per-type token totals by the configured unit prices to produce a **labeled estimate** stating its price basis (unit prices + effective date). With no price list, **no dollar figure appears anywhere**. A model present in the data but absent from the price list has its cost **omitted and labeled "unpriced"** — never guessed. The cost module is fully isolated: the token lens works end-to-end when `cost.py`/`prices.json` are absent.

**Rationale**: Implements FR-010 and Correctness (V): prices are volatile and user/plan-specific, so they are user-provided (also satisfying Local-Only — nothing is fetched) and every derived figure is an explicit estimate.

**Alternatives considered**: Bundle a default price table — rejected; it would drift, imply authority, and risk looking like a bill. Fetch prices — rejected (network forbidden).

---

## D8 — Reconciliation as a first-class golden test (SC-002)

**Decision**: A dedicated test asserts that, for **each** session, the four token-type totals equal the sum of that session's per-turn `usage`, with **zero discrepancy** — plus a sub-check that the per-model split also sums back to the session totals when multiple models are present. Surfaced as its own task in `tasks.md`, not folded into general testing.

**Rationale**: This is the guarantee behind the "exact" label. Making it its own golden test (as feature 002 did for the cube) makes the exactness continuously verifiable.

**Alternatives considered**: Spot-checking a few sessions — rejected; reconciliation must hold for all.

---

## Resolved unknowns summary

- Field locations, model id, timestamp: **confirmed by inspection** (D1).
- Growth-curve and over-time rendering (the two open items): **decided** (D4, D5) — inline SVG reusing 002's chart, downsampled series, reused bucketing.
- No third-party dependency is introduced; node remains dev-only test tooling.
