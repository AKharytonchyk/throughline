# Implementation Plan: Token-Lens Legibility

**Branch**: `004-token-lens-legibility` | **Date**: 2026-07-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-token-lens-legibility/spec.md`

## Summary

A surgical, **presentation-only** clarity pass on the feature-003 token-usage lens: make the token
terms **self-explanatory**. An always-visible one-line caption states the cache-read lesson, and
discoverable hover tooltips explain the four token types and the cache-read share, reusing the
existing shared tooltip mechanism. **No new data, no new parsing, no blob changes, no new Python
modules, and the occupancy lens is untouched.** Changes are confined to `report/app.js` (the
`renderTokenFlow` view) and `report/render.py` (CSS + static copy).

*(Repository linking was considered and dropped: the top-bar repository filter already answers
"which repo," so per-session repository display is not added — session rows stay as they are.)*

## Technical Context

**Language/Version**: Python 3.11+ (repo runs on 3.14); the dashboard's client is vanilla JS
inlined into the single HTML artifact (feature 002 pattern).

**Primary Dependencies**: None (Python standard library only). Node's built-in `node:test` remains
a dev-only runner and is untouched here (no new pure functions).

**Storage**: Unchanged — reads the already-built embedded blob; writes only the regenerated
`out/dashboard.html` under the working directory.

**Testing**: Existing `unittest` (stdlib) + `node --test` suites must stay green (proving the blob
and occupancy lens are unchanged). Feature behavior is DOM/copy, verified by a browser/screenshot
check (Playwright over a local `http.server`, since `file://` is blocked).

**Target Platform**: Local CLI + a single self-contained `dashboard.html` in any modern browser.

**Project Type**: Single project — CLI + static HTML report generator.

**Performance Goals**: No change; the added markup is O(rows) string building, negligible.

**Constraints**: 100% local, no network, offline-capable, one self-contained HTML file, no CDN/
external assets; transcripts read-only; all output inside the working directory.

**Scale/Scope**: Two functions in `app.js` (`renderTokenFlow`, `renderTokenGrowth`) + a handful of
CSS rules and copy strings in `render.py`. No data-layer or aggregation changes.

## Constitution Check

*GATE: must pass before Phase 0 and be re-checked after Phase 1.*

| Principle | Assessment |
|---|---|
| I. Local-Only | ✅ No network; copy is static text; repository comes from the already-local blob. |
| II. Privacy of Transcript Data | ✅ No new data read or written; output stays in the working directory. |
| III. Read-Only Toward Claude Code | ✅ Nothing touches Claude Code's domain. |
| IV. Observer, Not Participant | ✅ Pure presentation; no hooks or behavior changes. |
| V. Correctness Over Completeness | ✅ **Core fit.** Explanations describe figures truthfully (tokens are exact reads); no figure is mislabeled. |
| VI. Simple to Run | ✅ Same command, same single artifact. |
| VII. Think Before Coding | ✅ Trivial unknowns; resolved in research.md. |
| VIII. Simplicity First | ✅ Reuses the existing tooltip mechanism and repo-shortening; no new system, no new pure functions invented just to test. |
| IX. Surgical Changes | ✅ Two client functions + CSS/copy only; occupancy lens and all Python analysis untouched. |
| X. Goal-Driven Execution | ✅ SC-003/SC-004 (screenshot-legible headline; zero hover-only figures) are checkable. |
| Tech Constraints | ✅ Python + stdlib; no third-party runtime dependency; vanilla JS in the existing artifact. |

**Result: PASS.** No violations → Complexity Tracking empty.

## Project Structure

### Documentation (this feature)

```text
specs/004-token-lens-legibility/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (no new stored data — display-only)
├── quickstart.md        # Phase 1 output (browser/screenshot verification)
├── contracts/
│   └── client-behavior.md   # addendum to 003's client-behavior: repo column + explain layer
└── tasks.md             # Phase 2 (/speckit-tasks — not created here)
```

### Source Code (repository root)

**Extend (reuse, do not parallel):**

```text
src/throughline/report/
├── app.js       # renderTokenFlow: add data-tip/data-sub help on the four token-type labels + the
│                #   cache-read share; add an always-visible caption under the share callout.
│                # (NO new exported pure functions; the "By session" table is left unchanged.)
└── render.py    # CSS: .tkhelp (dotted-underline + cursor:help; a stub already exists) and caption
                 #   styling. Occupancy CSS untouched.
```

**No new files.** No changes to `parser/`, `analysis/`, `report/aggregate.py`, the blob schema, or
the occupancy views. No new tests files: this is DOM/copy with no new pure logic (per the
technical direction — do not invent pure functions just to add a unit test); regression is covered
by the existing suites plus the quickstart browser check.

**Structure Decision**: Single project, unchanged layout. The feature is a thin legibility layer on
top of the existing token lens; the only shared surface it relies on (the delegated
`data-tip`/`data-sub` tooltip) already exists.

## Complexity Tracking

> No constitution violations. Nothing to justify.
