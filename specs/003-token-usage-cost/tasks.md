---
description: "Task list for Token Usage & Cost (feature 003)"
---

# Tasks: Token Usage & Cost

**Input**: Design documents from `/specs/003-token-usage-cost/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: INCLUDED — the spec makes reconciliation (SC-002) a first-class golden test, and the project (features 001/002) carries stdlib unittest + dev-only `node --test` for client pure functions.

**Organization**: By user story (US1–US4) so each is independently implementable and testable. This feature is **additive** on 001/002 — reuse the named existing modules; the token (flow) model stays architecturally separate from the occupancy (chars) model (FR-001).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1–US4; Setup/Foundational/Polish carry no story label

## Path Conventions

Single project: `src/throughline/…`, `tests/…` at repo root (per plan.md).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: fixtures and module stubs needed by everything below.

- [X] T001 [P] Create synthetic token fixtures under `tests/fixtures/tokens/` — sessions where each assistant turn carries a `message.usage` block (input/output/cache_creation/cache_read) and `message.model`; include: a multi-model session, turns spanning multiple days, one long session (>240 turns, to exercise growth downsampling), and one session whose assistant turns have NO usage block.
- [X] T002 [P] Create module stubs `src/throughline/analysis/tokens.py` and `src/throughline/analysis/cost.py` (module docstrings + `from __future__ import annotations`; no logic yet).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: the flow-model backbone every story builds on. **⚠️ No user story can start until this phase is complete.**

- [X] T003 Extend `ParsedSession` in `src/throughline/parser/transcript.py` to capture per-turn usage for **main-thread** assistant turns: `input`←`input_tokens`, `output`←`output_tokens`, `cache_write`←`cache_creation_input_tokens`, `cache_read`←`cache_read_input_tokens` (missing ⇒ 0), plus `model`←`message.model` and the record `timestamp`; increment a `no_usage_turns` counter when a main-thread assistant turn has no `usage` block. Leave the existing `resident_tokens` read untouched.
- [X] T004 Implement the per-session flow builder in `src/throughline/analysis/tokens.py`: from a `ParsedSession`'s per-turn usage, produce `SessionTokenFlow` = `{turns, no_usage, totals(FlowTotals), by_model: model→FlowTotals}` (pure; `Σ by_model == totals`; no growth/by_day yet). (depends T003)
- [X] T005 In `src/throughline/report/aggregate.py`, add a **separate top-level `token_flow`** section to `build_embedded_data` per `contracts/embedded-token-flow.schema.json`: `unit:"tokens"`, `sessions:[{session,p,turns,no_usage,totals,by_model}]`, `models`, `coverage:{sessions_total,sessions_no_usage}`; emit `growth`/`by_day` as empty arrays for now; reuse the existing `dims.projects`/`dims.days` index tables; **do not modify `cube`/`session_facts`**. (depends T004)
- [X] T006 In `src/throughline/report/render.py`, add a view-layer lens switch (`Context window` ↔ `Token usage`, default `Context window`) and empty token-lens section containers + base CSS; leave all occupancy markup and the default view untouched.
- [X] T007 In `src/throughline/report/app.js`, wire the lens switch (show/hide occupancy vs token sections) and read the `token_flow` blob section; keep the occupancy aggregators/rendering untouched and default-visible. (depends T006)

**Checkpoint**: blob carries a separate token_flow section; dashboard can switch to an (empty) token lens.

---

## Phase 3: User Story 1 - Token flow by type (Priority: P1) 🎯 MVP

**Goal**: exact per-type token spend (input/output/cache-write/cache-read) with the cache-read share, per session and aggregated, labeled exact.

**Independent Test**: open the token lens on collected data → four types + cache-read share shown, per-session totals reconcile to recorded usage, and the lens is clearly separate from the chars lens.

### Tests for User Story 1

- [X] T008 [P] [US1] **Golden reconciliation test** in `tests/test_tokens.py`: for every fixture session, `Σ per-turn usage == SessionTokenFlow.totals` with zero discrepancy, and `Σ by_model == totals` (multi-model fixture). (SC-002, FR-009)
- [X] T009 [P] [US1] Test in `tests/test_tokens.py`: a session with assistant turns but no usage block sets `no_usage`; missing individual fields count as 0; `cache_read_share` = cache_read/total (0 when total is 0). (D2, FR-005)
- [X] T010 [P] [US1] Node test `tests/token_flow.test.mjs`: `flowTotals` and `flowByModel` sum a sample `token_flow` blob correctly and reconcile; `cache_read_share` correct.

### Implementation for User Story 1

- [X] T011 [US1] Implement exported pure fns `flowTotals(blob, filter)` and `flowByModel(blob, filter)` in `src/throughline/report/app.js` (tokens only; filter by project + day range; reuse the feature-002 `filter` object; never touch occupancy aggregates). (depends T007)
- [X] T012 [US1] Render the "Token flow by type" view in `src/throughline/report/app.js`: the four types + prominent cache-read share + a **per-model breakdown** (from `flowByModel`, reconciling to the total — FR-009) + a per-session table; label figures **exact**; show a coverage note when `coverage.sessions_no_usage > 0`. (depends T011)
- [X] T013 [US1] Add CSS for the token by-type bars/table in `src/throughline/report/render.py` (own token styling; not shared with occupancy classes — avoid the `.chip`-style collision seen earlier). (depends T006)

**Checkpoint**: MVP — the token lens shows exact by-type spend with reconciliation proven.

---

## Phase 4: User Story 2 - Re-billing growth over a session (Priority: P2)

**Goal**: a per-session cumulative curve showing context re-billed each turn.

**Independent Test**: pick a session → cumulative tokens rise across its turns, cache-read emphasized; the curve is downsampled but ends at the session's true totals.

### Tests for User Story 2

- [X] T014 [P] [US2] Test in `tests/test_tokens.py`: growth series is ≤120 points, always includes the first and last turn, is cumulative non-decreasing, and its final point equals the session totals. (D4)

### Implementation for User Story 2

- [X] T015 [US2] Add the downsampled growth-series builder to `src/throughline/analysis/tokens.py`: ≤120 `GrowthPoint`s, even sampling by turn index preserving first+last, cumulative per type. (depends T004)
- [X] T016 [US2] Populate `growth` per session in the `token_flow` section in `src/throughline/report/aggregate.py`. (depends T015, T005)
- [X] T017 [US2] Add `sessionGrowth(blob, sessionId)` + render the growth curve (inline SVG in the feature-002 chart style, session selector, cache-read emphasized) in `src/throughline/report/app.js`. (depends T011, T016)
- [X] T018 [US2] Add the growth-view container + CSS in `src/throughline/report/render.py`. (depends T006)

**Checkpoint**: US1 + US2 both work independently under the token lens.

---

## Phase 5: User Story 3 - Token spend over time (Priority: P3)

**Goal**: a per-day/week token trend honoring the repo/time filters and intervention markers.

**Independent Test**: with multi-day data → token trend plotted per bucket; filter + markers respond.

### Tests for User Story 3

- [X] T019 [P] [US3] Test in `tests/test_tokens.py`: `by_day` totals summed across days reconcile to the session totals; granularity (day vs week) chosen via `timeline.choose_granularity`.
- [X] T020 [P] [US3] Node test `tests/token_flow.test.mjs`: `flowByDay` aggregates by bucket, honors the project/day-range filter, and reconciles.

### Implementation for User Story 3

- [X] T021 [US3] Add `by_day` bucketing to `src/throughline/analysis/tokens.py`: bucket each turn by its own timestamp day, per project, summing the four types; reuse `src/throughline/analysis/timeline.py` (`day_of`). (depends T003)
- [X] T022 [US3] Populate `by_day` in the `token_flow` section in `src/throughline/report/aggregate.py`. (depends T021, T005)
- [X] T023 [US3] Implement `flowByDay(blob, filter)` + render the over-time trend by **reusing `lineChart`** in `src/throughline/report/app.js`, drawing the existing intervention markers and honoring the repo/time filters. For each intervention marker, also surface a numeric **before/after % change** in mean daily tokens, so the user can *read* the change, not just see it (SC-003). (depends T011, T022)
- [X] T024 [US3] Add the trend-view container + CSS in `src/throughline/report/render.py`. (depends T006)

**Checkpoint**: US1–US3 independently functional.

---

## Phase 6: User Story 4 - Optional dollar-cost estimate (Priority: P4)

**Goal**: an opt-in, empty-by-default, clearly-labeled cost estimate; token lens fully works without it.

**Independent Test**: no price list → no dollar figure anywhere; add `prices.json` → labeled estimate appears; unpriced models labeled, never guessed.

### Tests for User Story 4

- [X] T025 [P] [US4] Tests in `tests/test_cost.py`: absent/empty price list ⇒ `cost` absent / `available:false` and no figures; a priced model computes `tokens × unit_price` correctly; a model present in data but absent from the price list is flagged `priced:false` (omitted, not guessed); every figure carries an estimate label with its basis. (FR-010)

### Implementation for User Story 4

- [X] T026 [P] [US4] Add `price_list_path` + `load_price_list` to `src/throughline/config.py`, mirroring `load_interventions` (per `contracts/price-list.schema.json`); absent/empty file ⇒ empty price list.
- [X] T027 [US4] Implement the cost estimate in `src/throughline/analysis/cost.py`: per-model, per-type `tokens × unit_price` → a labeled estimate carrying the basis (`effective` + unit); models absent from the price list flagged unpriced; fully isolated so the token lens works when this module/file is absent. (depends T004, T026)
- [X] T028 [US4] In `src/throughline/report/aggregate.py`, attach the `cost` object to `token_flow` **only** when a non-empty price list loads (otherwise omit / `available:false`). (depends T027, T005)
- [X] T029 [US4] Render the cost view in `src/throughline/report/app.js`: shown only when `cost.available`; every dollar figure labeled an **estimate** with its price basis; unpriced models labeled; hidden entirely otherwise. (depends T011, T028)
- [X] T030 [US4] Add cost-view CSS in `src/throughline/report/render.py`. (depends T006)

**Checkpoint**: all four stories independently functional.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T031 [P] Update `README.md`: add the Token-usage lens to the feature list (exact per-type counts, cache-read re-billing, over-time trend, opt-in labeled cost estimate); note it is a separate lens from the chars view.
- [X] T032 Run the full suite green: `PYTHONPATH=src python3 -m unittest discover -s tests` and `node --test tests/token_flow.test.mjs`.
- [X] T033 Run `specs/003-token-usage-cost/quickstart.md` validation end-to-end (generate report, switch lens, verify each view with and without `prices.json`).
- [X] T034 [P] Verify constitution gates: no network during report; all output within the working directory; the occupancy lens (001/002) is unchanged and still the default.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (P1)**: no dependencies.
- **Foundational (P2)**: after Setup — **blocks all stories**. Order inside: T003 → T004 → T005; T006 → T007 (T006 may run parallel to T003/T004).
- **User Stories (P3–P6)**: all depend on Foundational. US1 is the MVP; US2/US3/US4 build on the US1 client aggregators (`flowTotals`) and the blob section but are otherwise independent and independently testable.
- **Polish (P7)**: after the desired stories.

### Story dependencies

- **US1 (P1)**: after Foundational. No dependency on other stories.
- **US2 (P2)**: after Foundational; reuses US1's `flowTotals`/lens plumbing (T011) for wiring but its curve is independent.
- **US3 (P3)**: after Foundational; reuses US1's `flowTotals` (T011) and 002's `lineChart`/markers.
- **US4 (P4)**: after Foundational; isolated cost module — token lens works fully without it.

### Within a story

Tests before implementation. Analysis (`tokens.py`/`cost.py`) → aggregate (`aggregate.py`) → client (`app.js`) → styling (`render.py`).

### Parallel opportunities

- Setup T001, T002 in parallel.
- US1 tests T008, T009, T010 in parallel (different files / independent).
- Cross-story: once Foundational is done, the *test* tasks and the analysis-layer tasks of US2/US3/US4 can be drafted in parallel; the `app.js` render tasks touch one file (app.js) so serialize those (T011→T012→T017→T023→T029).

---

## Parallel Example: User Story 1

```bash
# Tests first (parallel):
Task: "Golden reconciliation test in tests/test_tokens.py"           # T008
Task: "no_usage / missing-field / share test in tests/test_tokens.py" # T009  (same file as T008 → run after, or combine)
Task: "flowTotals/flowByModel node test in tests/token_flow.test.mjs" # T010
```

*(Note: T008 and T009 share `tests/test_tokens.py`; treat as sequential edits to one file even though both are [US1] tests.)*

---

## Implementation Strategy

### MVP first (US1 only)

1. Phase 1 Setup → 2. Phase 2 Foundational → 3. Phase 3 US1 → **STOP & VALIDATE**: token lens shows exact by-type spend + cache-read share; reconciliation golden passes. Demo-able.

### Incremental delivery

Foundation → US1 (MVP) → US2 (growth) → US3 (trend) → US4 (cost). Each adds value without changing the occupancy lens or breaking earlier stories.

---

## Notes

- `[P]` = different files, no incomplete dependency. Most `app.js` render tasks are NOT `[P]` (one file).
- Keep the token model and occupancy model separate at every layer (FR-001): separate blob section, separate aggregators, separate render sections; shared only `dims`, the 002 filter, and markers.
- Reuse over rebuild: extend `transcript.py`, `aggregate.py`, `render.py`, `app.js`, `timeline.py`, `config.py`; new files only `analysis/tokens.py`, `analysis/cost.py`, and tests/fixtures.
- New CSS must not reuse existing occupancy class names (avoid the `.chip`/`.preset` collision fixed earlier).
- Commit after each task or logical group. Do not commit unless asked.
