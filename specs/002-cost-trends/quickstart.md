# Quickstart & Validation: Cost Over Time — Experiment Tracker & Filters

Run/validation guide for feature 002. Builds on 001; reuses already-collected data. See
[contracts/](./contracts/) and [data-model.md](./data-model.md) for detail. Implementation
lives in the source tree; test bodies in `tests/`.

## Prerequisites

- Feature 001 present and data collected (`throughline collect` run at least once).
- Python 3.11+. No third-party packages.
- Some history spanning multiple days / projects / working modes (for meaningful trends).

## The two commands (unchanged) + notes

```bash
python3 -m throughline collect          # (001) still the only collection step
python3 -m throughline report --open    # now emits the interactive dashboard
python3 -m throughline note add --date 2026-07-03 --label "added Read offset/limit"
```

## Golden check (Python — the JS trust anchor)

```bash
PYTHONPATH=src python3 -m unittest tests.test_aggregate
```
Expected: summing the full (unfiltered) cube equals feature 001's breakdown totals and
heatmap counts (research.md D8). If this passes, the client — which only sums the cube — is
trustworthy by construction.

## Story validations

### US1 — Did my per-call optimization work? (P1, MVP)

1. Open the dashboard; find the **trend** view; select a heavy tool (e.g. `builtin:Read`).
2. Confirm it plots **average size per call** per time bucket, plus call count per bucket.
3. Confirm the metric is per-call (not a raw sum): a bucket where Read returned smaller
   slices reads lower even if its call count is similar/higher (SC-004).
4. If you recorded an intervention (`note add`), confirm a labeled marker appears at that
   date and the buckets after it are visibly lower when the change helped.

### US2 — Filter by repo and time range (P2)

1. In the filter bar, pick a single **project**; confirm every view (breakdown, heatmap,
   trend, mode, chains) recomputes to that project **instantly, without a re-run** (SC-007).
2. Set a **from/to** range; confirm all views reflect only that window; combine with project.
3. Clear filters; confirm the full view returns.
4. Set a filter that matches nothing; confirm an explicit empty state (FR-007).
5. Browser check: read a bucket total off the DOM after filtering and confirm it equals the
   independently summed cube cells for that project/range (validates JS aggregation).

### US3 — Is plan mode cheaper than auto? (P3)

1. Open the **mode** view; confirm cost is segmented by `plan / auto / acceptEdits / default`
   (and `unknown` if present), showing **both** average per session and average per call.
2. Confirm a session that changed mode mid-way splits its calls across the modes that were
   active (per-call attribution, FR-009).
3. Compare plan vs auto averages to state which cost less over the analyzed data (SC-003).

### US4 — Intervention markers (P4)

1. `note add --date … --label …`; regenerate `report`; confirm the marker shows on trends
   spanning that date. With no notes, trends render unmarked. `note list` / `note remove`
   behave as specified.

## Constitution gate checks (carried from 001)

| Gate | How to verify |
|------|---------------|
| Local-only (SC-006) | Load the dashboard with networking disabled; filtering/trends/mode all work offline. Grep the HTML for `http`/`<script src`/`cdn` — none. |
| Self-contained | The dashboard is one file; `app.js` and the data blob are inlined (no external requests). |
| Read-only | 001's read-only guarantees unchanged; `note`/`report` write only under `~/.throughline/`. |
| Estimates labeled (SC-005) | Resident, survival, and chain-saving figures keep the "estimate" badge after filtering; compaction retention stays "exact". |

## Performance (SC-007)

Apply/clear filters and switch trend tools repeatedly; each update re-renders client-side in
well under a second (target < ~200ms at the current data scale) with no tool re-run.
