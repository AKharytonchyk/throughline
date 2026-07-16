---
description: "Task list for Cost Over Time — Experiment Tracker & Filters (feature 002)"
---

# Tasks: Cost Over Time — Experiment Tracker & Filters

**Input**: Design documents from `/specs/002-cost-trends/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md.
**Builds on feature 001** (parser, analysis, report, cli already exist).

**Tests**: INCLUDED. Python data-prep is the trust anchor (unit tests + the **golden check**:
full cube sums == 001 totals). The client-side `app.js` **aggregation** is unit-tested with a
dev-only `node` script using the built-in `node:assert` (no JS framework / npm packages — not
a tool runtime dependency; node is a dev prerequisite for that one test). `app.js` view
*rendering* is validated by browser-driven checks (quickstart).

**Organization**: By user story, in spec priority order (US1 → US2 → US3 → US4).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: different files, no dependency on an incomplete task. **Tasks touching
  `app.js` are NOT parallel with each other** (same file).
- Paths are repo-relative; source under `src/throughline/`, tests under `tests/`.

## Path Conventions

- Single Python project extended in place. Runtime data under `~/.throughline/`.
- **Zero third-party dependencies** (Python stdlib; `app.js` is hand-written vanilla JS,
  inlined, no libraries/CDN).

---

## Phase 1: Setup

- [x] T001 Extend `tests/fixtures/`: add transcripts spanning **multiple projects and days**
  (varied timestamps), a session with a **mid-session mode change** (`permission-mode`
  records: auto→plan), and data supporting an intervention date — for trend/filter/mode tests
- [x] T002 [P] Add the interventions path (`~/.throughline/interventions.json`) to
  `src/throughline/config.py`

**Checkpoint**: fixtures + config paths ready.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: the mode signal, bucketing, the aggregate cube, and the `app.js` scaffold that
every story builds on.

**⚠️ CRITICAL**: no user story can complete until this phase is done.

- [x] T003 [P] Extend `src/throughline/parser/transcript.py`: track `permissionMode` by
  **file order** (from `permission-mode` records); stamp each `ToolCall.mode`
  (plan/auto/acceptEdits/default/unknown); `unknown` before the first mode record
  (research.md D3, FR-009)
- [x] T004 [P] New `src/throughline/analysis/timeline.py`: derive a UTC **day** from a
  timestamp; day↔week bucketing; auto-granularity chooser (daily ≤ ~14 days span, else
  weekly) (research.md D4, FR-001)
- [x] T005 New `src/throughline/report/aggregate.py`: build the sparse **cube**
  (`{p,d,t,m,sess}→{n,s}`) + `session_facts` (resident_est/non_tool/sidechain) + `dims`
  (projects/days/tools/modes) from parsed sessions — depends on T003, T004
- [x] T006 Extend `src/throughline/report/aggregate.py`: emit `chain_shapes` +
  `chain_occurrences` (reuse 001's sequence miner for shapes; tag each occurrence with
  p/d/sess/total_cost/intermediate), global `survival.by_tool`, carry 001's `compaction`
  block and `interventions`, and assemble the full `EmbeddedData` per
  contracts/embedded-data.schema.json — depends on T005
- [x] T007 Refactor `src/throughline/report/render.py`: emit the HTML shell + embed
  `EmbeddedData` as `<script type="application/json" id="thl-data">` + inline `app.js`;
  keep 001's Python-rendered views for now (US1 adds the trend; US2 ports them) — depends on T006
- [x] T008 New `src/throughline/report/app.js` scaffold: parse the `#thl-data` blob, expose
  `aggregate(filter)` (sum matching cube cells + session facts) and a render entrypoint
  (no views yet). Structure all aggregation as **pure, exported functions** with a
  `module.exports` guard (ignored in the browser) so they are unit-testable under `node`
  (contracts/client-behavior.md)
- [x] T009 [P] Write `tests/test_mode_timeline.py`: file-order mode attribution, `unknown`
  before first mode, mid-session change splits calls — covers T003
- [x] T010 [P] Write `tests/test_timeline.py`: day derivation, week bucketing, auto-granularity
  — covers T004
- [x] T011 [P] Write `tests/test_aggregate.py`: **GOLDEN** — summing the full cube reproduces
  001's breakdown totals and heatmap counts; dims + chain-occurrence correctness — covers T005/T006

**Checkpoint**: cube builds, golden check passes, `report` embeds the blob + app.js scaffold.

---

## Phase 3: User Story 1 — Did my per-call optimization work? (Priority: P1) 🎯 MVP

**Goal**: a per-tool **average-size-per-call over time** trend (plus overall), so a
before/after change (e.g. `Read` with offset/limit) is visible.

**Independent Test**: quickstart US1 — select `Read`, see avg-per-call by bucket + call
count; a smaller-per-call period reads lower even if call count rose.

- [x] T012 [US1] Implement trend aggregation in `src/throughline/report/app.js`: group cube by
  bucket (day→week auto) for a selected tool → `avg_per_call = Σs/Σn` + count; plus an overall
  trend (FR-002/003/004)
- [x] T013 [US1] Render the trend view in `src/throughline/report/app.js` (inline-SVG line chart)
  with a tool selector; add its container to the `render.py` shell (FR-001) — depends on T012, T007
- [x] T014 [P] [US1] Extend `tests/test_aggregate.py` with a per-tool per-bucket
  **avg-per-call reference** on a fixture (Python golden mirroring the JS trend math), incl.
  the "count rises while avg falls" case (SC-004)

**Checkpoint**: MVP — trustworthy per-tool cost-over-time trend from real data.

---

## Phase 4: User Story 2 — Filter by repo and time range (Priority: P2) · the big lift

**Goal**: filter every view by project + time range, instantly, client-side (no re-run).
This ports the remaining views into `app.js` so a filter drives them.

**Independent Test**: quickstart US2 — pick a project and/or range; all views recompute
instantly; clear restores; a no-match filter shows an explicit empty state.

- [x] T015 [US2] Port breakdown + budget-bar rendering into `src/throughline/report/app.js`
  (render from aggregated cube + session facts, incl. resident/non-tool/unattributed and
  mounted-but-unused) (FR-006) — depends on T008
- [x] T016 [US2] Port heatmap rendering into `src/throughline/report/app.js` (grouped cells;
  global survival shading, labeled "all data") (FR-006, D5) — depends on T015 (same file)
- [x] T017 [US2] Port chain-card rendering into `src/throughline/report/app.js` (filter
  occurrences → recurrence/avg-cost/score/rank; drop < `min_recurrence`; join shapes)
  (FR-006) — depends on T016 (same file)
- [x] T018 [US2] Remove the now-duplicated Python view builders (breakdown/heatmap/chains)
  from `src/throughline/report/render.py`; JS is the single renderer — depends on T017
- [x] T019 [US2] Add the filter bar (project selector + from/to range) and apply the filter
  predicate before aggregation in `src/throughline/report/app.js`; re-render all views on
  change; explicit empty state (FR-005/006/007) — depends on T015–T017
- [x] T020 [US2] Wire `report --project/--from/--to` presets → `initial_filter` in the blob
  (`src/throughline/cli.py` + `aggregate.py`) (contracts/cli.md, FR-005) — depends on T006
- [x] T021 [P] [US2] Browser validation (quickstart US2): filter updates all views instantly;
  a DOM total after filtering equals the independently summed cube for that subset

**Checkpoint**: every view filters live, client-side; Python no longer renders view HTML.

---

## Phase 5: User Story 3 — Is plan mode cheaper than auto? (Priority: P3)

**Goal**: context cost segmented by working mode, showing both per-session and per-call
averages.

**Independent Test**: quickstart US3 — mode view shows plan/auto/acceptEdits/default with
both metrics; a mid-session mode change splits its calls across modes.

- [x] T022 [US3] Compute mode segments in `src/throughline/report/app.js`: group filtered cube
  by mode → `avg_per_call = Σs/Σn` and `avg_per_session = Σs / distinct(sess)` (FR-008/010) — depends on T019
- [x] T023 [US3] Render the mode-comparison view in `src/throughline/report/app.js`
  (plan/auto/acceptEdits/default/unknown; both metrics side by side); add container to the
  `render.py` shell (FR-008/010) — depends on T022
- [x] T024 [P] [US3] Browser validation (quickstart US3): both metrics shown; mid-session
  mode split correct

**Checkpoint**: the plan-vs-auto comparison is answerable.

---

## Phase 6: User Story 4 — Mark when I made a change (Priority: P4)

**Goal**: dated intervention notes drawn as markers on trends.

**Independent Test**: quickstart US4 — `note add`, regenerate, see a labeled marker on trends
spanning that date; no notes ⇒ no markers.

- [x] T025 [US4] Implement the interventions store (read/write
  `~/.throughline/interventions.json`) in `src/throughline/config.py` and embed it into the
  blob in `aggregate.py` (FR-011) — depends on T002, T006
- [x] T026 [US4] Add `throughline note add|list|remove` to `src/throughline/cli.py`
  (contracts/cli.md) — depends on T025
- [x] T027 [P] [US4] Draw intervention markers on trends in `src/throughline/report/app.js`
  (FR-012) — depends on T013
- [x] T028 [P] [US4] Write `tests/test_interventions.py`: add/list/remove + embedding — covers T025/T026

**Checkpoint**: before/after interventions are visible on the trend.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [x] T029 [P] Self-contained/local audit: generated HTML has no external refs (`http`,
  `<script src`, `cdn`); `app.js` + data blob inlined; filtering/trends/mode work offline (SC-006)
- [x] T030 [P] Estimate-labeling audit after filtering: resident/survival/chain-saving figures
  keep the "estimate" badge; compaction retention stays "exact" (SC-005)
- [x] T031 [P] Performance check: filter/tool-selection re-render < ~200ms; `report` generation
  stays < 30s (SC-007)
- [x] T032 [P] Edge-case pass: empty-filter state, single-bucket trend, undated-record fallback
  to session mtime, `unknown` mode, no-interventions (spec Edge Cases)
- [x] T033 [P] Update `README.md` / quickstart with trends, filters, mode view, and the `note`
  command
- [x] T034 [P] Write `tests/app_aggregate.test.mjs` (dev-only, run with `node --test`, built-in
  `node:assert`, no packages): import `app.js`'s pure aggregation functions and assert, against
  a small fixture blob — the filter predicate (project/date passes), cube grouping for
  breakdown + per-tool trend (avg-per-call) + mode segments (per-call & per-session, incl. a
  session spanning modes), and chain-occurrence aggregation (recurrence/score below/above
  `min_recurrence`). Closes the client-math test gap (plan Testing) — depends on T019, T022

---

## Dependencies & Execution Order

### Phase order

Setup (P1) → Foundational (P2) → **US1 (P1)** → **US2 (P2)** → **US3 (P3)** → **US4 (P4)** →
Polish. This matches spec priority order.

### Cross-story dependencies

- Foundational (cube + `app.js` scaffold) blocks all stories.
- US1 adds the trend view (JS); 001's other views stay Python-rendered until US2.
- **US2 ports breakdown/heatmap/chains into `app.js`** and adds the filter — after US2, JS is
  the single renderer and the filter drives every view (incl. US1's trend).
- US3 (mode view) and US4 (markers) build on the US2 filter so they respect it.

### Within a phase

- `app.js` tasks are **sequential** (same file): T012→T013; T015→T016→T017→T019; T022→T023; T027.
- Python-module tasks in different files may be `[P]`: T003 ∥ T004 ∥ T002; foundational tests
  T009 ∥ T010 ∥ T011.
- Browser-validation tasks (T021, T024) and doc/audit tasks are `[P]`.

---

## Parallel Execution Examples

```text
# Foundational — different files:
T003 (parser mode)  |  T004 (timeline)      # then T005 → T006 → T007 (chain, same aggregate/render flow)
T009 (test_mode)    |  T010 (test_timeline) |  T011 (test_aggregate golden)

# Polish — all independent:
T029 | T030 | T031 | T032 | T033
```

---

## Implementation Strategy

### MVP (stop-and-validate after US1)

Setup → Foundational → **US1**. Delivers the headline: a trustworthy per-tool
avg-size-per-call trend over time. Validate via the golden check + quickstart US1.

### Incremental delivery

US1 (trend) → US2 (filters — the big JS port) → US3 (mode comparison) → US4 (markers) →
Polish. Each phase is independently testable; US2 is the largest and converts the dashboard
to client-side rendering.

---

## Notes

- The **cube is the Python↔JS contract**; the golden test (T011) is the trust anchor for all
  client-side aggregation.
- Interactive filtering is the one added complexity (plan Complexity Tracking); JS only sums a
  tested cube and uses no libraries.
- Survival under a filter uses the global per-tool rate (research.md D5), labeled "all data".
- Commit after each task or logical group; keep the golden check green before advancing.
