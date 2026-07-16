# Phase 0 Research: Cost Over Time — Experiment Tracker & Filters

Decisions for feature 002, grounded in a read-only inspection of real transcripts and in the
existing 001 codebase. **[observed]** = from real data; **[design]** = design choice;
**[clarified]** = fixed by `/speckit-clarify`.

---

## D1. Interactive filtering architecture — cube + client re-aggregation

**Decision**: **[clarified: interactive/client-side]** The Python analysis runs **once** at
`report` time and emits a compact, pre-aggregated **aggregate cube** embedded in the HTML.
A vanilla-JS app re-aggregates the filtered subset and re-renders all views on each filter
change. The browser performs only **summation/grouping over the cube** — it never re-runs
attribution, sizing, or the chain miner.

- **Cube cell**: `{project, day, tool, mode, session} → {count, size}` — one per distinct
  combination that had tool calls. Sparse: ≈ a few thousand cells for the current data
  (≤ one per tool call, usually fewer) **[observed: ~5.7k calls]**.
- **Session facts** (not per-tool): `{project, day, session} → {resident_est, non_tool,
  sidechain_size, sidechain_calls}` so the client can sum resident + non-tool for the
  filtered window.
- **Chain occurrences**: `{chain_id, project, day, session, total_cost, intermediate}` +
  **chain shapes** `{chain_id, steps, proposal}`; the client filters occurrences, recomputes
  recurrence/avg-cost/score, drops chains below `min_recurrence`, and re-ranks — no re-mining.
- **Dims** (index tables): `projects[]`, `days[]`, `tools[]` (with kind/server), `modes[]`.
- **Per-tool survival** (global) + **interventions** ride along.

**Rationale**: Delivers the instant, no-re-run UX the user chose while keeping the analysis
engine single-sourced in Python (Simplicity within the constraint). The cube is small and
JS summation over a few thousand rows is trivial.

**Alternatives considered**: Regenerate-per-filter CLI flags (simpler, my recommendation —
rejected by the user in clarify); re-running the full analysis in browser JS (rejected —
duplicates the engine, heavy, violates Simplicity); a local server that re-renders (rejected —
daemon, Principle VI).

---

## D2. View rendering moves to the client

**Decision**: **[design]** Because filters must update **all** views live, the filterable
views (breakdown + budget bar, heatmap, trend, mode, chains) are rendered by `app.js` from
the cube — on initial load and on every filter change. Python `render.py` is refactored to
emit the HTML shell (head/CSS/header/containers), embed the data blob, and inline `app.js`.
This avoids maintaining two renderers (Python + JS) for the same views.

**Rationale**: One renderer, fed by one data source; no divergence. Keeps the file
self-contained (app.js is inlined, no external asset).

**Alternatives considered**: Python renders initial + JS re-renders on filter (rejected —
duplicate view logic in two languages, drift risk).

---

## D3. Working-mode attribution — file-order tracking

**Decision**: **[design, grounded]** Attribute each tool call to the Claude Code working
mode active at that point by **scanning records in file order** and tracking the current
`permissionMode` from `permission-mode` records; a call before the first mode record is
`unknown` (never guessed, FR-026-style honesty).

- `permission-mode` records carry `{permissionMode, sessionId, type}` and **no timestamp**
  **[observed]** — so ordering is by file position, not time.
- Values observed: `default`, `auto`, `acceptEdits`, `plan` **[observed]**.
- Coverage: **5671/5766 tool calls (98.4%)** get a mode this way; 95 fall before any mode
  record → `unknown` **[observed]**.
- **Mode changes mid-session in 14/40 sampled sessions [observed]** — so per-call (not
  per-session) attribution is necessary; each call is stamped with `ToolCall.mode`.

**Rationale**: Grounded in the actual record shape; robust without timestamps.

**Alternatives considered**: Timestamp-ordering the mode records (rejected — they have no
timestamp); per-session single mode (rejected — modes change mid-session).

---

## D4. Time bucketing — daily cells, client re-buckets to weeks

**Decision**: **[clarified: auto by span]** Every tool call carries a timestamp
**[observed: 100% coverage]**. Python assigns each call a **day** (UTC date from its
timestamp) as the cube's finest time grain. The client chooses the display granularity by the
**filtered** span: daily for ≤ ~2 weeks, weekly (summing days) for longer. Bucketing to weeks
is pure summation of daily cells, so re-bucketing on filter is cheap and correct.

**Rationale**: Daily is the finest we'd ever show; weeks are aggregates of days, so one grain
(day) in the cube supports both, and a narrow date filter can still show daily detail.

**Alternatives considered**: Fixed weekly cells (rejected — can't show daily detail when
filtered to a short range); per-call rows (works but larger and needs client-side grouping
that the day-cell already does).

---

## D5. Survival under a filter — global per-tool rate (documented simplification)

**Decision**: **[design]** The per-tool survival estimate (001, from compaction summaries) is
computed **once over all data** and applied to heatmap shading regardless of the active
filter. It is **not** re-computed for the filtered subset.

**Rationale**: Re-computing survival per filter would require embedding pre/post compaction
text (large, sensitive) and re-running overlap in JS — disproportionate for a secondary,
already-labeled estimate. Correctness is preserved by labeling: survival stays an
estimate, and the UI notes it reflects all data, not the current filter.

**Alternatives considered**: Embed per-session survival contributions (rejected — bloat + JS
complexity for marginal value); drop survival under filter (rejected — losing the shading
is worse than a labeled global approximation).

---

## D6. Interventions store

**Decision**: **[design]** Dated notes live in `~/.throughline/interventions.json`
(`[{date, label}]`), managed by `throughline note add|list|remove`, embedded into the blob at
generation, and drawn as marker lines on trends. Local file, within the working directory.

**Rationale**: Simplest local persistence; matches 001's config idiom; keeps the tool's
"observer" stance (notes are the user's own annotations, not Claude Code data).

---

## D7. Embedding & size

**Decision**: **[design]** The blob is embedded as `<script type="application/json"
id="thl-data">…</script>` (JSON, `html.escape` for `</`), read by `app.js`. Estimated size
for current data: cube (~few-thousand cells) + occurrences + dims ≈ a few hundred KB —
acceptable for a local file, no network. No compression needed.

**Rationale**: Standard self-contained-embedding technique; keeps the single-file guarantee.

**Alternatives considered**: External `.json` sidecar (rejected — breaks single-file / needs
`fetch`, which `file://` blocks and which is a network-shaped call); base64 (unneeded).

---

## D8. Testing strategy

**Decision**: **[design]** Python data-prep is unit-tested (stdlib `unittest`): mode-timeline
attribution, day/week bucketing, cube builder, chain-occurrence emission, interventions store.
**Golden check**: summing the full (unfiltered) cube MUST reproduce feature 001's breakdown
totals and heatmap counts — this makes the JS trustworthy since JS only sums the cube. The JS
filtering/rendering is validated by **browser-driven** checks in quickstart (apply a filter,
read the DOM numbers, compare to an independently computed expectation).

**Rationale**: Puts correctness where it's cheap and deterministic (Python), and treats the
cube as the contract between Python and JS. Avoids adding a JS test framework (dependency).

**Alternatives considered**: A JS unit-test runner (rejected — third-party dependency,
violates Technology Constraints).

---

## Resolved unknowns

No `NEEDS CLARIFICATION` remain. The clarified decisions (interactive/client-side; auto-span
buckets; both per-session & per-call mode metrics) are reflected above. The one honest
simplification (global survival under filter, D5) is labeled in the UI, consistent with
Principle V.
