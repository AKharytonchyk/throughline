# Implementation Plan: Burn-Down / Biggest Levers

**Branch**: `005-burn-down-levers` | **Date**: 2026-07-20 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/005-burn-down-levers/spec.md`

## Summary

Add a single **burn-down** panel that ranks reduction **levers** — mounted-but-unused MCP tools, collapsible tool chains, and long re-billing sessions — each with a projected **per-day token saving** (and opt-in `$/day`), sorted by impact, plus an aggregate "if you act on these" figure with a non-additive caveat. It is advisory only and adds no new collection.

Technical approach: the analysis already runs once in Python and is re-aggregated **client-side** in `app.js` on every filter change (features 002/003). Levers therefore compute **client-side** so they honor the repo/time filter instantly (US3). Two small, filter-independent facts are missing from the embedded blob and must be added by `aggregate.py`: (1) an estimated **per-tool resident token size** for each mounted tool (to price an unmount lever), and (2) per-model **unit prices** (to dollarize a scope-specific token saving; the existing `cost` blob only carries whole-dataset computed dollars). A new pure `aggregateLevers(blob, filter)` in `app.js` composes the existing `aggregateBreakdown` (unused tools), `aggregateChains` (`est_saved` chars), and `token_flow` (turns, cache-read, per-day) signals into ranked levers; a new token-lens section renders them. Every projected figure is a labeled estimate stating its method.

## Technical Context

**Language/Version**: Python 3.11+ (analysis + blob build); vanilla ES5-style JavaScript in `app.js` (client render/aggregation). No change to either runtime.

**Primary Dependencies**: None. Python standard library only; `app.js` uses no libraries (constitution: stdlib-only, no external assets).

**Storage**: Read-only Claude Code transcripts under `~/.claude/projects`; all output under the working dir (`~/.throughline`). Optional user-provided `prices.json` (already supported, feature 003). No new files.

**Testing**: `python3 -m unittest` (stdlib unittest) for the Python blob additions + a golden reconciliation; `node --test tests/*.mjs` for the new pure `aggregateLevers` client aggregator (dev-only, mirrors `app_aggregate.test.mjs` / `token_flow.test.mjs`).

**Target Platform**: Local CLI producing a single self-contained `dashboard.html` opened in a browser. Offline.

**Project Type**: Single project (CLI + analysis + self-contained HTML report). Existing `src/throughline/` layout.

**Performance Goals**: Client re-aggregation stays interactive (<~50ms) on realistic session counts; the two new blob tables are O(mounted tools) and O(priced models) — negligible size growth.

**Constraints**: No network (prices are embedded from the local file, never fetched). No new long-running process. One artifact, no external assets. Every estimate labeled with method.

**Scale/Scope**: Single user, single machine, own sessions. New blob tables are one row per mounted tool and one row per priced model — small.

## Constitution Check

*GATE: must pass before Phase 0 and re-checked after Phase 1 design.*

| Principle | Status | How this feature complies |
|-----------|--------|---------------------------|
| I. Local-Only Operation | ✅ PASS | No network. Prices come from the already-local `prices.json`, embedded into the blob at generation time; nothing is fetched. |
| II. Privacy of Transcript Data | ✅ PASS | No transcript-derived byte leaves the working dir; the blob is embedded in the same `dashboard.html` produced today. |
| III. Read-Only Toward Claude Code | ✅ PASS | Read-only inputs only; no writes into Claude Code's domain. |
| IV. Observer, Not Participant | ✅ PASS | **Advisory only.** Names what to unmount/collapse/shorten; never installs or enforces caps and never changes Claude Code behavior. This is the explicit line (FR-010). |
| V. Correctness Over Completeness | ✅ PASS | Every projected saving is labeled an **estimate** with a stated method; per-tool resident inherits its existing estimate label; the aggregate states its overlap/non-additive caveat; "no significant levers" is stated rather than fabricated. |
| VI. Simple to Run | ✅ PASS | Same two commands, same single artifact; no new process, flag, or file required. |
| VII. Think Before Coding | ✅ PASS | Research (Phase 0) records the space→flow conversion, the per-day basis, and the two blob gaps before code. |
| VIII. Simplicity First | ✅ PASS | Reuses existing aggregators and blob sections; adds one client function, one render section, two small blob tables. No new abstraction. |
| IX. Surgical Changes | ✅ PASS | Additive: new `aggregateLevers` + new `tview-burndown` section + two blob fields. Existing views' section indices shift by one (display-only). No refactor of working code. |
| X. Goal-Driven Execution | ✅ PASS | Each user story has an Independent Test; quickstart defines runnable verification; golden reconciliation guards the resident-by-tool split. |

**Technology Constraints**: Python + stdlib only; no third-party dependency added; `app.js` stays library-free. **PASS.**

**Result: PASS — no violations, Complexity Tracking not required.**

## Project Structure

### Documentation (this feature)

```text
specs/005-burn-down-levers/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   ├── embedded-levers.schema.json   # blob additions (mounted_resident, token_flow.unit_prices)
│   └── client-behavior.md            # aggregateLevers + rendering contract
└── tasks.md             # Phase 2 (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
src/throughline/
├── analysis/
│   ├── sizing.py        # (reuse) resident_estimate().per_tool — source of per-tool resident chars
│   ├── breakdown.py     # (reuse) unmount-candidate signal
│   ├── sequences.py     # (reuse) chain est_saved signal
│   ├── tokens.py        # (reuse) per-session turns / cache_read / by_day
│   └── cost.py          # (reuse) price-list parsing; source of unit prices to embed
├── report/
│   ├── aggregate.py     # EDIT: embed `mounted_resident` table + `token_flow.unit_prices`
│   ├── render.py        # EDIT: add <section id="tview-burndown"> to the token lens; bump other indices
│   └── app.js           # EDIT: add pure aggregateLevers() + renderBurndown(); wire into renderTokens()

tests/
├── test_levers_blob.py          # NEW: mounted_resident + unit_prices shape + golden reconciliation
├── burndown.test.mjs            # NEW: node --test for aggregateLevers (ranking, per-day, $, empty)
└── fixtures/levers/             # NEW: sessions with an unused tool, a chain, and a long session
```

**Structure Decision**: Single existing project. The burn-down view lives in the **Token-usage lens** (`#token-views`) because its outputs are in the flow unit (tokens/day, opt-in `$/day`); the occupancy lens already shows the raw signals (unmount candidates, chains) and gains a one-line pointer to it. All lever math is client-side in `app.js` (to honor the live filter), fed by two additive blob tables built once in `aggregate.py`.

## Complexity Tracking

No constitution violations — no entries required.
