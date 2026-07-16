---
description: "Task list for Token-Lens Legibility (feature 004)"
---

# Tasks: Token-Lens Legibility

**Input**: Design documents from `/specs/004-token-lens-legibility/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: NOT INCLUDED as new unit tests — this is DOM/copy work with **no new pure logic** (per the
plan and research D4; the constitution's Simplicity forbids inventing pure functions just to test
static text). Verification is the existing suites staying green (blob/occupancy unchanged) plus a
browser/screenshot check.

**Organization**: One user story (US1 — explain the terms). Additive, presentation-only on the
feature-003 token lens; the occupancy lens and the embedded blob are untouched (FR-007).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1; Setup/Polish carry no story label

## Path Conventions

Only two files change: `src/throughline/report/app.js` and `src/throughline/report/render.py`.

---

## Phase 1: Setup (baseline anchor)

- [X] T001 Confirm the baseline suites are green before changes (regression anchor for SC-003): `PYTHONPATH=src python3 -m unittest discover -s tests` and `node --test tests/token_flow.test.mjs tests/app_aggregate.test.mjs`.

---

## Phase 2: User Story 1 - Understand what the token terms mean (Priority: P1) 🎯

**Goal**: the token flow view teaches its own terms — an always-visible cache-read caption plus
discoverable hover explanations on the four token types and the cache-read share.

**Independent Test**: open the token lens → a plain-language cache-read caption is visible without
hovering; the four types + share show a help affordance and reveal explanations on hover; no key
figure's meaning is hover-only.

### Implementation for User Story 1

- [X] T002 [P] [US1] In `src/throughline/report/render.py` finalize the `.tkhelp` affordance CSS (dotted underline + `cursor:help`, already stubbed) and add caption styling (e.g. `.tkcaption`: muted, readable, sits under the share callout). Occupancy CSS untouched. (FR-004)
- [X] T003 [US1] In `src/throughline/report/app.js` `renderTokenFlow`, attach `data-tip` (type name) + `data-sub` (plain-language meaning) and the `.tkhelp` class to each of the four token-type labels (input / output / cache-write / cache-read), using the copy in data-model.md; reuse the existing delegated hover tooltip — do NOT add a new tooltip system. (FR-002, FR-004, FR-006)
- [X] T004 [US1] In `renderTokenFlow`, attach `data-tip`/`data-sub` + `.tkhelp` to the cache-read **share** callout so hovering it explains why a high share is expensive. (FR-003, FR-004)
- [X] T005 [US1] In `renderTokenFlow`, add the **always-visible** one-line caption element directly under the cache-read share callout stating the headline lesson in plain language (never hover-gated); ensure it reads sensibly at 0% and at a dominant share. (FR-001, FR-005)

**Checkpoint**: the token flow view is self-explanatory; nothing meaningful is hover-only.

---

## Phase 3: Polish & Verification

- [X] T006 Run the full suites green (SC-003 — proves the blob and occupancy lens are unchanged): `PYTHONPATH=src python3 -m unittest discover -s tests` and `node --test tests/token_flow.test.mjs tests/app_aggregate.test.mjs`.
- [X] T007 Browser/screenshot verification per `quickstart.md` (Playwright over a local `http.server`, since `file://` is blocked): confirm the caption is legible in a static screenshot (SC-001) and that the four types + share expose discoverable hover tooltips with no hover-only meaning (SC-002).

---

## Dependencies & Execution Order

- **Setup (T001)**: first — establishes the green baseline.
- **US1 (T002–T005)**: T002 (render.py CSS) may run in parallel with the `app.js` tasks (different
  file); T003 → T004 → T005 are sequential edits to the **same** function (`renderTokenFlow`) in the
  one file `app.js`, so serialize them.
- **Polish (T006–T007)**: after US1 is complete.

## Parallel opportunities

- T002 (render.py) ∥ the first app.js task, since they are different files.
- The three `renderTokenFlow` edits (T003–T005) touch one function → not parallel.

## Implementation Strategy

Single increment: finalize the CSS affordance, add the four type tooltips + the share tooltip, add the
always-visible caption, then verify (suites green + browser/screenshot). No data-layer or occupancy
changes at any step.

## Notes

- Reuse over rebuild: the delegated `data-tip`/`data-sub` tooltip already exists (feature 002/003);
  this feature only supplies content + a discoverability affordance.
- Do not add blob fields, parsing, analysis, or new Python modules (FR-007). Do not touch the
  occupancy lens or the "By session" table (repository linking is out of scope).
- Commit after the story or logical group. Do not commit unless asked.
