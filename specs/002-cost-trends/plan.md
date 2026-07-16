# Implementation Plan: Cost Over Time — Experiment Tracker & Filters

**Branch**: `002-cost-trends` | **Date**: 2026-07-15 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-cost-trends/spec.md`

**Note**: Increment on feature 001 (Throughline). Grounded in a read-only inspection of the
real transcripts (mode signal, timestamps) — see [research.md](./research.md). No source or
Claude Code files were modified during planning.

## Summary

Add a time dimension, filtering, and a working-mode comparison to the existing local
dashboard, so the developer can measure whether their own changes (e.g. `Read` with
`offset`/`limit`, or switching to plan mode) reduced context cost. No new collection: it
reuses feature 001's copied transcripts.

Technical approach (driven by the clarified **interactive/client-side** decision): the
Python analysis runs **once** at `report` time and emits a compact, pre-aggregated
**aggregate cube** (`{project, day, tool, mode, session} → {count, size}`) plus per-session
facts (resident estimate, non-tool, sidechain), chain **occurrences** + shapes,
per-tool survival, dimension tables, and interventions — all embedded as one JSON blob in
the HTML. A hand-written vanilla-JS app in the page reads the blob and, on every filter
change, **re-aggregates the matching subset and re-renders** all views (context breakdown,
heatmap, the new per-tool time trend, the mode comparison, and chain cards). The browser
only sums a Python-built, Python-tested cube — it does **not** re-run attribution, sizing,
or the chain miner. Still one command, zero network, zero third-party dependencies; the JS
is inlined (no CDN, no libraries).

## Technical Context

**Language/Version**: Python 3.11+ (extends the 001 codebase). Standard library only. The
emitted dashboard gains an inlined vanilla-JS layer (no framework, no CDN).

**Primary Dependencies**: **None (standard library only).** The client-side app is
hand-written vanilla JS kept in a packaged `app.js` and inlined at generation (read via
`pathlib`/`importlib.resources`); it fetches nothing.

**Storage**: Reuses `~/.throughline/` (001's copied transcripts). Adds
`~/.throughline/interventions.json` (dated notes, US4). Output is still the single
self-contained `dashboard.html` (now larger — it embeds the aggregate cube).

**Testing**: `unittest` (stdlib). Python data-prep is the priority target and is fully
testable: mode-timeline attribution, day/week bucketing, the aggregate-cube builder
(**golden check**: summing the full cube reproduces 001's breakdown totals), chain-occurrence
emission, and the interventions store. The client-side **aggregation** in `app.js` is
unit-tested with a dev-only `node` script (built-in `node:assert`, no framework / npm
packages — not a tool runtime dependency; node is a dev prerequisite for that one test),
which imports `app.js`'s pure exported functions. `app.js` view *rendering* is verified by
browser-driven checks in quickstart (apply a filter, read the DOM, compare to an
independently computed expectation).

**Target Platform**: Local developer machine, macOS/Linux, terminal + local browser.

**Project Type**: Single project — CLI tool emitting a static, now-interactive HTML artifact.

**Performance Goals**: Filter/selection changes re-render **instantly** client-side
(target < ~200ms for the observed data scale); `report` generation stays within the
001 budget (< 30s). Embedded cube is sparse (~a few thousand cells for the current data).

**Constraints**: No network (SC-006). All writes within the working directory. The dashboard
remains a single self-contained file openable via `file://` — the embedded JS is inlined,
no external assets. Exact figures exact; estimates (resident, survival, savings) labeled.

**Scale/Scope**: ~50 sessions, ~5.7k tool calls, ~30 projects, weeks of history. Cube stays
small; the JS handles a few thousand rows trivially.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution v1.1.0.

| Principle | Gate | Status |
|-----------|------|--------|
| I. Local-Only | JS is inlined; data embedded; no fetch/CDN/network. Verifiable offline (SC-006). | PASS |
| II. Privacy | The embedded cube (sizes, tool names, project paths, chain ids) stays in the HTML under the working directory; nothing transmitted. | PASS |
| III. Read-Only Toward Claude Code | Unchanged — reads 001's copies read-only; new writes (interventions) go only to the working dir. | PASS |
| IV. Observer | No new Claude Code interaction; no hooks added by this increment. | PASS |
| V. Correctness Over Completeness | Cube preserves exact per-call/non-tool sizes; resident/survival/savings stay labeled estimates; the exact compaction retention is unchanged; mode is "unknown" (not guessed) before the first mode record; survival shading under a filter uses the global per-tool rate — a **documented simplification**, labeled. | PASS |
| VI. Simple to Run | Still `collect` + `report`; no daemon. Interactive filtering adds a client-side rendering layer (see Complexity Tracking) — the only real complexity increase, and user-directed. | PASS (noted) |
| VII–X (discipline) | Ambiguities resolved in clarify; formats grounded in real data; JS confined to summation over a tested cube; changes are additive to 001. | PASS |
| Technology Constraints | Python stdlib only (the tool). The dashboard's inline vanilla JS is hand-written — not a third-party dependency, no libs/CDN. | PASS |
| Dev Workflow & Gates | No network, writes confined, estimates labeled, no unjustified dependency. | PASS |

**Result**: No violations. One justified complexity increase recorded below.

## Project Structure

### Documentation (this feature)

```text
specs/002-cost-trends/
├── plan.md              # This file
├── research.md          # Phase 0 — decisions (interactive architecture, mode timeline, …)
├── data-model.md        # Phase 1 — cube, facts, occurrences, dims, embedded blob
├── quickstart.md        # Phase 1 — runnable validation per user story (browser-driven)
├── contracts/
│   ├── embedded-data.schema.json   # the JSON blob the JS consumes
│   ├── client-behavior.md          # filter controls + re-aggregation + render contract
│   └── cli.md                      # report filter presets + `note` command additions
└── tasks.md             # Phase 2 (/speckit-tasks — NOT created here)
```

### Source Code (repository root) — changes to the existing tree

```text
src/throughline/
├── parser/
│   └── transcript.py        # EXTEND: track permission-mode by file order; stamp ToolCall.mode
├── analysis/
│   └── timeline.py          # NEW: timestamp→day, day↔week bucketing helpers
├── report/
│   ├── aggregate.py         # NEW: build cube + session facts + chain occurrences + dims + interventions -> embedded-data dict
│   ├── model.py             # EXTEND: reuse 001 analysis for chain SHAPES + survival; hand off to aggregate.py
│   ├── render.py            # REFACTOR: emit shell + embed data blob + inline app.js (views now rendered by JS)
│   └── app.js               # NEW: vanilla-JS app — filter controls, re-aggregation, view renderers, intervention markers
├── collector/               # (unchanged)
├── config.py                # EXTEND: interventions.json path
└── cli.py                   # EXTEND: report --project/--from/--to presets; `note add|list|remove`
tests/
├── fixtures/                # EXTEND: multi-project, multi-day, mode-change, intervention fixtures
├── test_mode_timeline.py    # NEW
├── test_timeline.py         # NEW (bucketing)
├── test_aggregate.py        # NEW (cube golden check, occurrences, dims)
└── test_interventions.py    # NEW
```

**Structure Decision**: Extend the single 001 project. The one architectural change is that
**view rendering moves to the client** (`app.js`) so filters can update everything instantly;
Python's job shifts from rendering view HTML to building the tested aggregate cube + emitting
the shell and inlined app. This is the direct, minimal consequence of the interactive choice
and avoids duplicating render logic in both Python and JS.

## Complexity Tracking

| Violation / added complexity | Why needed | Simpler alternative rejected because |
|------------------------------|------------|--------------------------------------|
| Client-side JS rendering + filtering layer (`app.js`) | US2 requires filters to update **all** views instantly without re-running the tool (clarified: interactive/client-side). | **Regenerate-per-filter CLI flags** (`report --project/--from/--to` re-rendering a static file) is simpler and was my recommendation, but the user explicitly chose interactive in `/speckit-clarify` for instant exploration. Mitigations keep it bounded: JS only **sums a Python-built, Python-tested cube** (no analysis duplicated), uses no libraries, and the cube has a golden test against 001's totals. |
