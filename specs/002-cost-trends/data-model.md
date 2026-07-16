# Phase 1 Data Model: Cost Over Time — Experiment Tracker & Filters

Extends feature 001's model. The Python side builds these; the client consumes the
`EmbeddedData` blob and derives the view models (TrendPoint, ModeSegment, filtered breakdown)
on the fly. Types are advisory; validation traces to FR-### / SC-### in spec 002.

---

## ToolCall (extended, 001)

Add one field:

| Field | Type | Notes |
|-------|------|-------|
| `mode` | enum | Working mode active at this call: `plan`\|`auto`\|`acceptEdits`\|`default`\|`unknown` — from file-order `permission-mode` tracking (research.md D3, FR-009). |

`ToolCall.timestamp` (already present, 100% populated) supplies the call's **day**.

---

## Dims (index tables in the blob)

Compact indices so cube cells can reference small integers.

| Field | Type | Notes |
|-------|------|-------|
| `projects` | list[str] | Repo/project paths; cell `p` indexes here. |
| `days` | list[str] | Sorted `YYYY-MM-DD` (UTC); cell `d` indexes here. |
| `tools` | list[object] | `{key, kind, server?, tool?}` (e.g. `builtin:Read`, `mcp:acme-mcp/getIssue`); cell `t` indexes here. |
| `modes` | list[str] | `["plan","auto","acceptEdits","default","unknown"]`; cell `m` indexes here. |

---

## CubeCell (the aggregate cube — FR-001, FR-002, FR-005, FR-008)

One per distinct `(project, day, tool, mode, session)` that had ≥1 tool call.

| Field | Type | Notes |
|-------|------|-------|
| `p` | int | project index |
| `d` | int | day index |
| `t` | int | tool index |
| `m` | int | mode index |
| `sess` | int | session index (for distinct-session counts in the mode view) |
| `n` | int | call count |
| `s` | int | total content size (chars) — input + output (per-call cost) |

**Rules**: cells are exact (sum of measured sizes). Summing the **full** cube MUST reproduce
001's per-tool per-call totals and counts (golden check, research.md D8). The client filters
by `p` and `d`-range, then groups by `t` (breakdown/heatmap), by `d` (trend), or by `m`
(mode).

---

## SessionFact (resident / non-tool / sidechain per session)

Not per-tool, so kept separate; the client sums over filtered sessions.

| Field | Type | Notes |
|-------|------|-------|
| `p`, `d`, `sess` | int | project / day / session indices (for filtering) |
| `resident_est` | int | per-session resident estimate (001 D7); labeled estimate |
| `non_tool` | int | main-thread non-tool content size (incl. attachments) |
| `sidechain_size`, `sidechain_calls` | int | reported separately (001 D4) |

---

## ChainOccurrence + ChainShape (view 3 under filter — FR-006)

Mined once by 001's sequence miner; the client filters occurrences and re-ranks (no re-mine).

**ChainShape**: `{chain_id, steps: [{signature, fanout}], proposal: {suggested_name, inputs,
output}}`

**ChainOccurrence**:

| Field | Type | Notes |
|-------|------|-------|
| `chain_id` | str | joins to ChainShape |
| `p`, `d`, `sess` | int | for filtering |
| `total_cost` | int | cost of this occurrence |
| `intermediate` | int | intermediate payload size (for est. saving) |

**Rules**: client groups filtered occurrences by `chain_id` → `recurrence = count`,
`avg_cost`, `score = recurrence × avg_cost × (1 − survival)`; hides chains with
`recurrence < min_recurrence`; ranks by score. `est_context_saved` recomputed from filtered
intermediates.

---

## Survival (global, per tool)

| Field | Type | Notes |
|-------|------|-------|
| `by_tool` | map<toolIdx, float?> | global per-tool survival rate, or null | 
| `available` | bool | false ⇒ heatmap shows no shading; labeled "reflects all data" (D5) |

---

## Intervention (US4 — FR-011/012)

| Field | Type | Notes |
|-------|------|-------|
| `date` | str | `YYYY-MM-DD` |
| `label` | str | short note (e.g. "added Read offset/limit") |

Stored at `~/.throughline/interventions.json`; embedded in the blob; drawn as marker lines on
trends spanning the date.

---

## Derived (client-computed view models — not embedded)

- **TrendPoint** `{bucket, avg_per_call, total_size, call_count}` — for a selected tool (or
  overall), per bucket; `avg_per_call = total_size / call_count` (FR-002/003).
- **ModeSegment** `{mode, total_size, call_count, sessions, avg_per_call, avg_per_session}`
  — `avg_per_session = total_size / (distinct sessions containing that mode)` (FR-010). A
  session that used multiple modes is counted in **each** mode's `sessions`, so the per-mode
  session counts overlap and do not partition sessions — the view labels this.
- **Filtered breakdown / heatmap** — over the filtered cell set. Resident is a single
  **aggregate** estimate bucket (Σ `resident_est`), not 001's per-tool heuristic split;
  mounted-but-unused is derived from `mounted_keys` (mounted tools with 0 calls in the window).

---

## EmbeddedData (the blob — analysis → client contract)

Top-level object embedded in `dashboard.html`; schema in
`contracts/embedded-data.schema.json`.

| Field | Type |
|-------|------|
| `generated_at` | str |
| `unit` | `"chars"` \| `"bytes"` |
| `dims` | Dims |
| `cube` | list[CubeCell] |
| `session_facts` | list[SessionFact] |
| `chain_shapes` | list[ChainShape] |
| `chain_occurrences` | list[ChainOccurrence] |
| `survival` | Survival |
| `compaction` | object | (001's exact retention block, carried through) |
| `interventions` | list[Intervention] |
| `min_recurrence` | int |
| `initial_filter` | object? | `{project?, from?, to?}` preset from CLI (FR-005) |

**Rules**: everything estimate-derived carries a flag/label so the client renders the
"estimate" badge; exact sizes are exact. The blob is the single Python↔JS contract.

---

## Relationships

```text
ParsedSession* (001) ──+ mode timeline (D3) ──> ToolCall.mode
ToolCall* ──aggregate──> CubeCell*         (grouped by p,d,t,m,sess)
ParsedSession* ─────────> SessionFact*     (resident/non_tool/sidechain)
ToolCall* ──001 miner──> ChainShape* + ChainOccurrence*
compaction summaries ──001──> Survival (global)
interventions.json ──> Intervention*
  → EmbeddedData ──(inlined)──> app.js ──filter+aggregate+render──> all views
```
