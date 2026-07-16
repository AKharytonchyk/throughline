# Implementation Plan: Token Usage & Cost

**Branch**: `003-token-usage-cost` | **Date**: 2026-07-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-token-usage-cost/spec.md`

## Summary

Add a **token-usage lens** to the existing dashboard — a second analysis view, architecturally separate from the context-window (chars) lens. It reports exact per-turn token counts (input / output / cache-write / cache-read) summed per session and per model, a per-session re-billing growth curve, a tokens-over-time trend, and an opt-in, empty-by-default dollar-cost estimate. The approach is **additive and reuses** the existing parser, session model, time-bucketing, filters, and dashboard scaffolding from features 001/002; it only adds a new read of three already-present `usage` fields and a new, self-contained flow data-model + views. Sub-agent attribution is explicitly deferred to feature 004.

## Technical Context

**Language/Version**: Python 3.11+ (repo runs on 3.14).

**Primary Dependencies**: None (Python standard library only). Dashboard interactivity is vanilla JS inlined into the single HTML artifact (continuation of the pattern established and justified in feature 002). Node's built-in `node:test` is used **only as a dev-time test runner** for the client-side pure functions — it is not a runtime dependency and ships nothing.

**Storage**: Files under the working directory (`~/.throughline`): read-only *copies* of Claude Code transcripts (already collected), the generated `out/dashboard.html`, and a new user-editable `prices.json` (empty by default) for the optional cost estimate.

**Testing**: `unittest` (stdlib) for Python; `node --test` for the client aggregation pure functions (dev-only, as in 002).

**Target Platform**: Local CLI + a single self-contained `dashboard.html` opened from `file://` in any modern browser. No server.

**Project Type**: Single project — CLI + static HTML report generator.

**Performance Goals**: `report` completes over tens–hundreds of sessions in a few seconds; the embedded JSON blob stays small by embedding **aggregates** (per-session totals, per-day buckets, per-model totals) plus a **downsampled** growth series — never raw per-turn arrays.

**Constraints**: 100% local, no network, offline-capable; every output inside the working directory; transcripts treated as read-only (copy before processing); one self-contained HTML file, no CDN/external assets; two commands only.

**Scale/Scope**: Single user; dozens–hundreds of sessions; individual sessions can reach ~10k assistant turns (this is what drives growth-curve downsampling — see research D4).

## Constitution Check

*GATE: must pass before Phase 0 and be re-checked after Phase 1.*

| Principle | Assessment |
|---|---|
| I. Local-Only | ✅ No network. Prices are user-provided in `prices.json`, never fetched. |
| II. Privacy of Transcript Data | ✅ Reads token counts from already-copied transcripts; all output stays in the working directory. |
| III. Read-Only Toward Claude Code | ✅ Only reads transcripts (already copied by `collect`); adds nothing to Claude Code's domain. |
| IV. Observer, Not Participant | ✅ Pure measurement; no new hooks or behavior changes. |
| V. Correctness Over Completeness | ✅ **Core fit.** Token counts are read verbatim from `usage` → labeled **exact** (FR-004). The dollar estimate is labeled an estimate with its price basis (FR-010). No per-tool token figure is presented as exact (FR-011). |
| VI. Simple to Run | ✅ Same two commands; the lens ships inside the existing single artifact. |
| VII. Think Before Coding | ✅ Unknowns resolved in research.md before coding; growth/trend rendering left open then decided. |
| VIII. Simplicity First | ✅ Reuse over rebuild; the cost module is isolated and optional; no speculative config. |
| IX. Surgical Changes | ✅ Extends named existing modules; does not refactor the occupancy lens. |
| X. Goal-Driven Execution | ✅ Reconciliation (SC-002) is a first-class, checkable golden test. |
| Tech Constraints | ✅ Python + stdlib; **no third-party runtime dependency added**; node is dev-only test tooling. |

**Result: PASS.** No violations → Complexity Tracking is empty. (The interactive client-side JS inside the self-contained HTML is not a new deviation; it is the same approach already justified for feature 002, and it is part of the delivered artifact, not a third-party dependency.)

## Project Structure

### Documentation (this feature)

```text
specs/003-token-usage-cost/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── embedded-token-flow.schema.json   # the separate `token_flow` blob section
│   ├── price-list.schema.json            # prices.json format
│   └── client-behavior.md                # lens switch + token-view aggregation
└── tasks.md             # Phase 2 (/speckit-tasks — not created here)
```

### Source Code (repository root)

**Extend (reuse, do not parallel):**

```text
src/throughline/
├── parser/transcript.py      # ParsedSession/ToolCall + parse loop (usage read at ~L153-155).
│                             #   ADD: capture per-turn usage (all 4 types + model + timestamp);
│                             #   flag turns/sessions with no usage block. Leave resident_tokens as-is.
├── analysis/timeline.py      # REUSE day_of/week_of/choose_granularity/bucket_of for the over-time trend.
├── config.py                 # ADD price_list_path + load_price_list (mirrors interventions loader); empty default.
├── report/aggregate.py       # build_embedded_data → ADD a separate top-level `token_flow` section
│                             #   (NOT merged into `cube`/`session_facts`). May reuse dims (project/day INDEX
│                             #   tables only) — never a shared totals/aggregate object.
├── report/render.py          # ADD a view-layer lens switch + token-view containers + CSS. Occupancy views untouched.
└── report/app.js             # ADD flow aggregation pure fns + token views + lens switch.
                              #   REUSE lineChart for the over-time trend and the 002 filter object/markers as-is.
```

**Add (new, isolated):**

```text
src/throughline/analysis/tokens.py   # pure: per-session TokenFlow (by type, by model), downsampled
                                     #   cumulative-over-turns series, per-day buckets, reconciliation helper.
src/throughline/analysis/cost.py     # pure + isolated: apply prices.json → labeled cost estimate;
                                     #   token lens works fully when this module/price list is absent.
tests/test_tokens.py                 # incl. the SC-002 reconciliation GOLDEN test (its own test).
tests/test_cost.py                   # opt-in/empty-default, unpriced-model omission+label.
tests/token_flow.test.mjs            # node dev-only: client flow aggregation pure fns.
tests/fixtures/tokens/               # synthetic multi-model, multi-day, long-session fixture(s).
```

**Structure Decision**: Single project, unchanged layout. The token lens lives beside the occupancy lens in the same package and the same generated artifact. The **architectural boundary** (FR-001) is enforced by a separate `token_flow` blob section, separate client aggregation functions, and separate render sections — the only shared surfaces are the `dims` index tables (projects/days), the feature-002 filter object, and the intervention markers. The two lenses never share a totals object or units.

## Complexity Tracking

> No constitution violations. Nothing to justify.
