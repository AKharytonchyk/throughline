---
description: "Task list for feature 005 — Burn-Down / Biggest Levers"
---

# Tasks: Burn-Down / Biggest Levers

**Input**: Design documents from `specs/005-burn-down-levers/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ (all present)

**Tests**: INCLUDED — the spec's quickstart requires a Python golden reconciliation and
`node --test` client aggregation checks.

**Organization**: Tasks are grouped by user story (P1→P4). Each story is an independently
testable increment. All lever math is client-side in `app.js`; two additive blob fields are
built once in `aggregate.py`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1–US4 for user-story tasks; none for Setup/Foundational/Polish
- Exact file paths are included in every task

## Path Conventions

Single project: `src/throughline/`, `tests/` at repo root (per plan.md).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Fixtures the tests and manual validation depend on.

- [X] T001 [P] Fixtures exercising all three lever types. **Done by reuse** (no new JSONL): the node `aggregateLevers` test uses a hand-built blob with an unused tool + a chain + a long session; the Python blob test reuses `tests/fixtures/proj-demo` (real MCP tools + resident); and `scripts/gen_demo.py` now emits 3 marathon sessions (>150 turns) so the hosted demo exercises the session-length lever end-to-end.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Embed the two facts the client lacks and stand up the burn-down section shell + the `aggregateLevers` skeleton. **No user story can begin until this phase is complete** (the client cannot compute a lever without these blob fields).

**⚠️ CRITICAL**: Blocks all of Phase 3+.

- [X] T002 Embed the disclosed `chars_per_token` factor (from `Config`) as a top-level blob field in `build_embedded_data` in `src/throughline/report/aggregate.py` (client needs it to convert chain chars→tokens).
- [X] T003 Build and embed the `mounted_resident` table — one row per mounted tool `{key, resident_tokens_est, is_estimate:true, method}`, where `resident_tokens_est = sizing.resident_estimate().per_tool[key] / chars_per_token` averaged over sessions where the tool is mounted — in `src/throughline/report/aggregate.py` (conforms to `contracts/embedded-levers.schema.json`).
- [X] T004 [P] Write `tests/test_levers_blob.py`: assert `chars_per_token` present; `mounted_resident` shape + `is_estimate`/`method`; the **golden reconciliation** that `Σ per-tool resident (×chars_per_token) + system_prompt_size ≈ resident_est` per session; **and** that each embedded `resident_tokens_est` equals the mean, over sessions where that tool is mounted, of `per_tool[key] / chars_per_token` (guards the averaged table itself, not just `sizing`).
- [X] T005 Add `<section class='viewsec' id='tview-burndown'></section>` as the **first** child of `#token-views` and bump the existing token sections' display indices to `02..05` in `src/throughline/report/render.py`; add a one-line pointer from the occupancy lens's "Mounted but unused" line to the burn-down section.
- [X] T006 Scaffold the pure `aggregateLevers(blob, filter)` in `src/throughline/report/app.js` — compute the **basis** only (`active_days` = distinct filtered days present in `token_flow.by_day`, matching `flowByDay`; `turns_per_day`; `small_sample` when `active_days < 3`) and return an empty `BurndownSummary`; export it on `API`; add a `renderBurndown()` stub and wire it into `renderTokens()` (renders the section, empty for now).

**Checkpoint**: Blob carries `chars_per_token` + `mounted_resident`; token lens shows an (empty) Biggest-levers section; `aggregateLevers` exists and is node-importable.

---

## Phase 3: User Story 1 — Ranked levers by projected daily token saving (Priority: P1) 🎯 MVP

**Goal**: A ranked list of levers (unmount / chain / session-length), each with a projected per-day token saving, sorted largest-first, each with a plain-language action and an estimate label + method.

**Independent Test**: With the fixtures, open Token usage → Biggest levers; confirm levers appear, each with a `tokens/day` figure and `est` chip, sorted descending, top row = largest saving; hover shows the method. (No prices configured → tokens only.)

- [X] T007 [US1] Implement the **unmount lever** in `aggregateLevers` — for each key in `aggregateBreakdown(blob, filter).unused` with a `mounted_resident` row: `tokens_per_day = resident_tokens_est × turns_per_day`; attach `type:"unmount"`, `action`, `method` — in `src/throughline/report/app.js`.
- [X] T008 [US1] Implement the **chain lever** in `aggregateLevers` — for each chain from `aggregateChains(blob, filter)`: `tokens_per_day = est_saved × recurrence / blob.chars_per_token / active_days`; `type:"chain"`, `action` (from proposal), `method` — in `src/throughline/report/app.js`.
- [X] T009 [US1] Implement the **session-length lever** in `aggregateLevers` — define the disclosed constant `LONG_SESSION_TURNS = 150`; over filtered `token_flow` sessions with `turns > LONG_SESSION_TURNS`, estimate post-threshold `cache_read` from each session's `growth.cum_read`, sum, divide by `active_days`; one aggregate `type:"session_length"` lever whose `action`/`method` state the 150-turn threshold — in `src/throughline/report/app.js`.
- [X] T010 [US1] Add ranking + significance floor + empty handling to `aggregateLevers` — drop any lever below the absolute floor (`tokens_per_day < LEVER_FLOOR_TPD`, = 1,000 tokens/day) or with zero/negative saving, sort by `tokens_per_day` desc, set `empty_reason` when none survive — in `src/throughline/report/app.js`.
- [X] T011 [US1] Implement `renderBurndown` ranked list — per lever: `title`, `action`, human-scaled `tokens/day`, `est` chip, `method` on hover (dotted-underline pattern); cap the unmount list to the **top 8** with a "+K more" line; explicit no-levers message when `empty_reason` — in `src/throughline/report/app.js` (reuse existing CSS classes; add minimal new classes in `render.py` `_CSS` only if needed).
- [X] T012 [P] [US1] Write `tests/burndown.test.mjs` (`node --test`): unmount/chain/session per-day math on the fixtures, descending order (SC-004), floor drops trivial levers, empty scope → `empty_reason` (SC-005), and every returned lever carries a non-empty `method` (SC-002).

**Checkpoint**: MVP — ranked token-savings levers render and are correct; works with no price list.

---

## Phase 4: User Story 2 — Opt-in dollar savings (Priority: P2)

**Goal**: When `prices.json` is configured, each lever and the aggregate also show a projected `$/day` (labeled estimate, price basis); with no prices, no `$` appears anywhere and tokens still show.

**Independent Test**: Rebuild with no `prices.json` → no `$` anywhere. Add per-model prices, rebuild → `$/day` per lever with basis; an in-scope model absent from prices is named as excluded.

- [X] T013 [US2] Embed `token_flow.unit_prices` (per-model `{input,output,cache_write,cache_read}`, `currency/effective/unit_label/per_million`) from the parsed price list, gated exactly like the existing `token_flow.cost`, in `src/throughline/report/aggregate.py`.
- [X] T014 [US2] Extend `tests/test_levers_blob.py`: `unit_prices.available` present only when a non-empty price list is loaded; absent otherwise (no `$` path).
- [X] T015 [US2] Implement the **dollarize** step in `aggregateLevers` — scope-blended `cache_read` $/token from `flowByModel(blob, filter)` × `unit_prices.by_model` (unpriced models excluded → `unpriced_models`); set each lever's `dollars_per_day`, else `null` — in `src/throughline/report/app.js`.
- [X] T016 [US2] Render `$/day` per lever + the price basis (`effective`, `unit_label`) + the unpriced-model note in `renderBurndown`; guarantee **no** `$` renders when `unit_prices` is absent — in `src/throughline/report/app.js`.
- [X] T017 [P] [US2] Extend `tests/burndown.test.mjs`: priced scope yields `$/day`; no `unit_prices` → all `dollars_per_day` null and no `$`; a model missing a price is excluded and surfaced in `unpriced_models` (SC-003).

**Checkpoint**: US1 + US2 — token savings always, dollars only when the user opts in.

---

## Phase 5: User Story 3 — Scope-aware recomputation (Priority: P3)

**Goal**: Levers, savings, and the per-day basis recompute for the repo/time filter, with the active-days basis stated and a small-sample flag for short windows.

**Independent Test**: Change repo, then date range — levers/savings/basis recompute instantly; a `<3`-active-day window shows the small-sample note.

- [X] T018 [US3] Surface the basis line (`active_days`, `turns_per_day`) and the `small_sample` note (when `active_days < 3`) in `renderBurndown` in `src/throughline/report/app.js`.
- [X] T019 [P] [US3] Extend `tests/burndown.test.mjs`: a repo filter and a date-range filter each change `aggregateLevers` output (levers set and `basis`) as expected; `active_days == 0` → empty state, no divide-by-zero.

**Checkpoint**: US1–US3 — the view is trustworthy across projects and windows.

---

## Phase 6: User Story 4 — Aggregate "if you act on these" figure (Priority: P4)

**Goal**: A single headline aggregate saving (tokens/day, and $/day when priced) with an explicit non-additive/overlap caveat.

**Independent Test**: Confirm the aggregate figure appears at the top of the section with a visible statement that per-lever savings may overlap and are not guaranteed to sum.

- [X] T020 [US4] Compute `aggregate_tokens_per_day` / `aggregate_dollars_per_day` + `overlap_caveat:true` in `aggregateLevers` in `src/throughline/report/app.js`.
- [X] T021 [US4] Render the "if you act on these" headline with the explicit overlap/non-additive caveat in `renderBurndown` in `src/throughline/report/app.js`.
- [X] T022 [P] [US4] Extend `tests/burndown.test.mjs`: aggregate equals the sum of shown levers and the summary always carries `overlap_caveat` (SC-006).

**Checkpoint**: All four stories independently functional.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T023 [P] Update `README.md` with a Biggest-levers subsection (burn-down cut-list; advisory; tokens + opt-in $) and a screenshot placeholder under `assets/screenshots/`.
- [X] T024 [P] Regenerate the hosted demo via `scripts/gen_demo.py` so the synthetic demo dashboard includes the burn-down section.
- [X] T025 Run full regression: `PYTHONPATH=src python3 -m unittest discover -s tests` and `node --test tests/*.mjs` — all green.
- [X] T026 Walk `quickstart.md` scenarios 1–5 in the built `dashboard.html`; confirm SC-001..SC-006, that the burn-down section renders **no** cap-installing/enforcing control (advisory only, FR-010), and that no network access and no writes outside the working directory occur.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: none — start immediately.
- **Foundational (Phase 2)**: after Setup; **blocks all user stories**.
- **User Stories (Phase 3–6)**: all depend on Foundational. US1 is the MVP. US2/US3/US4 each build on US1's `aggregateLevers`/`renderBurndown` (they extend the same function), so they proceed in priority order rather than fully in parallel.
- **Polish (Phase 7)**: after the desired stories are complete.

### User Story Dependencies

- **US1 (P1)**: after Foundational. No dependency on other stories. Standalone MVP.
- **US2 (P2)**: after US1 (adds the dollarize step + `unit_prices` blob). US1 remains valid with no prices.
- **US3 (P3)**: after US1 (adds basis surfacing + filter tests). Independent of US2.
- **US4 (P4)**: after US1 (aggregates the levers US1 produces). Independent of US2/US3.

### Within Each User Story

- Tasks editing `src/throughline/report/app.js` (the shared `aggregateLevers`/`renderBurndown`) are **sequential** among themselves.
- `node --test` extensions to `tests/burndown.test.mjs` run after that story's `app.js` logic lands; they are `[P]` relative to render-only tasks in the same phase (different file).

### Parallel Opportunities

- T001 (fixtures) is independent.
- In Foundational: T004 (Python test) `[P]` runs alongside T005 (render.py) / T006 (app.js).
- In each story, the story's `node --test` task `[P]` runs alongside the render-only task in that phase.
- In Polish: T023 (README) and T024 (demo) are `[P]`.

---

## Parallel Example: Foundational

```bash
# After T002+T003 (aggregate.py) land, these touch different files and can run together:
Task: "T004 golden reconciliation test in tests/test_levers_blob.py"
Task: "T005 burn-down section shell in src/throughline/report/render.py"
# T006 (app.js) follows T005 (its stub renders into the new section id).
```

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Phase 1 (fixtures) → Phase 2 (blob fields + section shell + `aggregateLevers` skeleton).
2. Phase 3 (US1): the three lever computations + ranking/floor/empty + ranked-list render.
3. **STOP and VALIDATE**: quickstart Scenario 1 + `node --test tests/burndown.test.mjs`.
4. Demo — this alone answers "where do I cut first," in tokens.

### Incremental Delivery

1. Foundational → US1 (MVP, tokens) → validate.
2. US2 (opt-in $) → validate no-price and priced paths.
3. US3 (scope-aware basis) → validate filter recompute.
4. US4 (aggregate headline + caveat) → validate.
5. Polish (README, demo, regression, quickstart walk).

---

## Notes

- `[P]` = different files, no dependency on an incomplete task.
- All lever math stays client-side in `app.js`; Python only embeds raw facts (Principle: analysis runs once).
- Every projected figure is a labeled **estimate** with a stated method; the view is **advisory** — no cap-installing/enforcing control anywhere (Principle IV).
- No network, no third-party dependency, single self-contained artifact (Principles I, VI; Tech Constraints).
- Commit after each task or logical group.
