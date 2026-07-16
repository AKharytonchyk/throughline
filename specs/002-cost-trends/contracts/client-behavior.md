# Contract: Client-Side Filtering & Rendering (`app.js`)

The inlined vanilla-JS app reads `EmbeddedData` (embedded-data.schema.json) and owns
rendering of the filterable views. No network, no libraries. It only **sums/groups** the
cube — it never re-runs attribution, sizing, or the chain miner.

## Filter state

```
Filter = { project: string|null, from: string|null (YYYY-MM-DD), to: string|null }
```

- A **filter bar** sits above the views with: a **project** selector (All + each
  `dims.projects`) and a **time range** (from / to; presets like "last 2 weeks" allowed).
- Initial state = `initial_filter` (from CLI presets) or empty (all data).
- Changing or clearing a filter re-runs aggregation + re-render **synchronously in the
  browser** (FR-006), target < ~200ms. No page reload, no `report` re-run (SC-007).
- A **cell passes** the filter iff (`project` null OR `dims.projects[cell.p] == project`)
  AND (`from` null OR `days[cell.d] >= from`) AND (`to` null OR `days[cell.d] <= to`).
  Session facts and chain occurrences filter by the same predicate.
- Empty result ⇒ every view shows an explicit empty state (FR-007), not stale content.

## View recomputation (from the filtered subset)

| View | Computation |
|------|-------------|
| **Breakdown + budget bar** | Group passing cells by `t` → Σ`s`, Σ`n`. Add resident (Σ `resident_est` over passing session_facts), non-tool (Σ `non_tool`), unattributed. Shares over the summed total. Mounted-but-unused = tools with 0 calls in subset. |
| **Heatmap** | Per tool from grouped cells → `{calls: Σn, volume: Σs}`; shade by `survival.by_tool[t]` (global; labeled "all data", D5). |
| **Trend (US1)** | For the selected tool (default: largest by volume, e.g. `Read`): passing cells for that `t`, grouped by bucket → `avg_per_call = Σs/Σn`, plus `Σn`. Also an **overall** trend (all tools). Bucket = **day** if filtered span ≤ ~14 days else **week** (sum days into weeks). Draw intervention markers at their dates. |
| **Mode (US3)** | Group passing cells by `m` → `avg_per_call = Σs/Σn` and `avg_per_session = Σs / (distinct sess with that mode)`. Show both, side by side. A session that used multiple modes counts toward each mode's session set (overlap, not a partition) — **label this** in the view so it is not misread. |
| **Chains (US3→ view 3)** | Group passing occurrences by `chain_id` → `recurrence = count`, `avg_cost`, `score = recurrence × avg_cost × (1−survivalₐᵥ𝗀)`; drop `recurrence < min_recurrence`; rank desc; join `chain_shapes` for steps + proposal; `est_saved` from Σ intermediates ÷ recurrence. |

## Trend metric rule (FR-002/003, SC-004)

The primary trend metric is **average per call** (`Σs / Σn`) per bucket — NOT a raw sum.
A raw-total series MAY be offered as a secondary toggle but MUST NOT be the only metric, so a
rise in call count cannot mask a drop in per-call size.

## Rendering & a11y

- Renders re-theme with the page (CSS variables); light/dark toggle unaffected.
- Estimate-derived figures (resident, survival, chain savings) keep the "estimate" badge;
  exact figures unbadged. The compaction retention stays labeled "exact".
- Keyboard-operable filter controls; `prefers-reduced-motion` respected for any transitions.
- Self-contained: `app.js` and data are inlined; no external requests (verifiable offline).

## Non-goals

- No re-mining of chains client-side; no re-computation of survival per filter (global, D5).
- No persistence of filter state across reloads (a filter is a view, not saved data).
