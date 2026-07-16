# Phase 1 Data Model: Throughline — Context Budget Analyzer

Internal, in-memory/on-disk data structures (plain Python dataclasses + JSON). No database.
All persisted data lives under the working directory. Field types are advisory; validation
rules trace to the spec's Functional Requirements (FR-###).

---

## Config

Persisted at `~/.throughline/config.json`.

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `transcript_dir` | path | `~/.claude/projects` | Discovery root (D2). |
| `working_dir` | path | `~/.throughline` | Only location the tool writes (FR-003). |
| `output_path` | path | `<working_dir>/out/dashboard.html` | Single HTML artifact. |
| `size_unit` | enum | `chars` | `chars` \| `bytes` (D6, FR-009). |
| `chars_per_token` | float | `4.0` | Disclosed factor, resident estimate only (D7). |
| `min_recurrence` | int | `2` | Threshold to call a chain "recurring" (D9, spec Assumptions). |
| `max_ngram` | int | `6` | Longest chain length mined (D9). |
| `hooks_opt_in` | object | `{installed:false}` | Consent + install marker (D10). |

**Rules**: no network fields; all paths resolved under user home; `working_dir` must exist
or be creatable; refuse to write anywhere outside it.

---

## SessionRef

A discovered transcript (before parsing).

| Field | Type | Notes |
|-------|------|-------|
| `session_id` | str | Transcript UUID (filename stem) [observed]. |
| `project` | str | Decoded project path (dir name, `-`→`/`). |
| `source_path` | path | Original transcript (read-only). |
| `copy_path` | path | Copy under `working_dir/transcripts/` (parsed instead of source). |
| `mtime`, `size_bytes` | num | For listing/filtering and change detection. |

**Rules**: `source_path` is never opened for write; parsing always uses `copy_path`
(FR-002, SC-007).

---

## ToolCall (normalized)

One per completed tool invocation; the parser's primary output (ordered per session).

| Field | Type | Notes |
|-------|------|-------|
| `session_id` | str | Owning session. |
| `index` | int | Position/order within the session (FR-005). |
| `tool_use_id` | str | Links `tool_use` → `tool_result` [observed]. |
| `name` | str | Raw tool name (e.g. `Bash`, `mcp__acme-mcp__getIssue`). |
| `bucket` | enum | `builtin` \| `mcp` \| `unattributed` (FR-014). |
| `server` | str? | For `mcp`: `<server>` segment (FR-011). |
| `tool` | str? | For `mcp`: `<tool>` segment. |
| `input` | any | Tool input (may be size-only if from PostToolUse log). |
| `input_size` | int | Size of input in `size_unit` (exact, D6). |
| `output_size` | int | Size of returned content in `size_unit` (exact, D6). |
| `is_error` | bool | From `tool_result.is_error` [observed]. |
| `timestamp` | str | ISO timestamp [observed]. |
| `caller` | str? | From `tool_use.caller` [observed]. |
| `is_sidechain` | bool | Subagent thread flag (D4). |
| `cli_wrapped_from` | str? | Set to `"Bash"` when re-attributed from CLI-wrapped MCP (D5). |

**Rules**: every ToolCall maps to exactly one bucket; unresolved identity → `unattributed`
(FR-014). Re-attribution (D5) sets `bucket=mcp`, `server`/`tool`, and `cli_wrapped_from`.

---

## ContextBucket (aggregate, view 1)

Aggregated across all sessions by default; also computable per session (FR-030).

| Field | Type | Notes |
|-------|------|-------|
| `key` | str | e.g. `builtin:Bash`, `mcp:acme-mcp/getIssue`, `resident`, `non_tool`, `unattributed`. |
| `kind` | enum | `builtin` \| `mcp_tool` \| `resident` \| `non_tool` \| `unattributed`. |
| `cost_kind` | enum | `per_call` \| `resident` (FR-013). |
| `total_size` | int | Sum of content size in `size_unit`. |
| `call_count` | int | Frequency; `0` for mounted-but-unused tools (FR-015). |
| `share` | float | `total_size` ÷ whole-window total (FR-012, D6). |
| `is_estimate` | bool | True for `resident` (D7); false for exact per-call/non-tool. |

**Rules**: buckets partition the **main-thread context window** and sum to its total size
(FR-014, SC-006). The `non_tool` bucket covers messages, thinking, and attachments/files
read; an explicit `unattributed` bucket captures the residual. `resident` buckets are
per-tool and flagged `is_estimate=true` with method text (D7). Subagent/sidechain volume is
tracked separately (see ReportData `sidechain`) and excluded from these buckets (D4).

---

## MountedTool

The set of tools available in a session, including never-called ones (D7b). Sourced from
`preCompactDiscoveredTools` (preferred, MCP tool-level) or local config (fallback, MCP
server-level) — **not** the transcript's called-tools view.

| Field | Type | Notes |
|-------|------|-------|
| `name` | str | `builtin` bare name, or `mcp:<server>/<tool>` (tool-level) / `mcp:<server>` (server-level). |
| `bucket` | enum | `builtin` \| `mcp`. |
| `server` | str? | For MCP. |
| `source` | enum | `discovered` (preCompactDiscoveredTools) \| `builtin_list` \| `mcp_config` \| `plugin`. |
| `granularity` | enum | `tool` (built-ins, and MCP when discovered) \| `server` (MCP config fallback, D7b). |
| `called_count` | int | `0` ⇒ mounted-but-unused (FR-015). |
| `est_schema_size` | int | Per-tool resident estimate (D7); labeled estimate. |

## ResidentEstimate

Per-tool resident (schema) cost — **always a labeled estimate** (D7; FR-006/009/025).

| Field | Type | Notes |
|-------|------|-------|
| `session_id` | str | |
| `total_overhead_size` | int | R = first-request `cache_creation_input_tokens × chars_per_token` [observed]. |
| `system_prompt_size` | int | Estimated constant S; shown as its own resident line (D7). |
| `per_tool` | map<str,int> | Heuristic split of `R − S` across mounted tools (D7). |
| `method` | str | Disclosed method string shown in UI (FR-025). |
| `is_estimate` | bool | Always `true`. |

---

## CompactionEvent

Read from each `system`/`compact_boundary` record's `compactMetadata` [observed]. The
compacted **summary** is the following `user` record flagged `isCompactSummary` (D8).

| Field | Type | Notes |
|-------|------|-------|
| `session_id` | str | |
| `trigger` | str | `auto` \| `manual` (from `compactMetadata.trigger`). |
| `pre_tokens` | int | `compactMetadata.preTokens` — EXACT. |
| `post_tokens` | int | `compactMetadata.postTokens` — EXACT. |
| `discovered_tools` | set[str] | `compactMetadata.preCompactDiscoveredTools` — real mounted set (D7b). |

**Rules**: `post_tokens / pre_tokens` is an **exact** context-retention ratio (labeled
exact, not estimate). Absence of any compaction summary ⇒ per-tool survival "unavailable"
(FR-026). The optional PreCompact backup (D10) is insurance only; survival reads the
transcript.

---

## SurvivalEstimate

| Field | Type | Notes |
|-------|------|-------|
| `scope` | enum | `tool` \| `chain`. |
| `key` | str | Tool bucket key or chain id. |
| `survival_rate` | float? | Fraction of the tool's distinctive returned values reappearing in the summary; `null` when unavailable. |
| `available` | bool | False ⇒ show "estimate unavailable", never a number (FR-026). |
| `method` | str | Method text (value overlap vs post-compaction summary, D8). |

**Rule**: `survival_rate` is **always** presented as an estimate with method (FR-025); it is
distinct from the exact `CompactionEvent` retention ratio.

---

## Chain (Pattern, view 3)

| Field | Type | Notes |
|-------|------|-------|
| `chain_id` | str | Stable hash of the step signature sequence. |
| `steps` | list | Ordered step signatures (attributed identities); a fan-out step marked `fanout=true` counts as one logical step (FR-020). |
| `data_edges` | list | `(k → k+1)` links proven by output→input value overlap (FR-019, D9). |
| `recurrence` | int | Occurrences across sessions; ≥ `min_recurrence` to qualify. |
| `total_cost` | int | Total context size the chain consumes per occurrence (sum of step sizes). |
| `intermediate_never_essential` | int? | Estimated intermediate payload that didn't survive (FR-021); `null` if survival unavailable. |
| `survival` | ref | `SurvivalEstimate(scope=chain)`. |
| `score` | float | `recurrence × total_cost × (1 − survival_rate)`; falls back to `recurrence × total_cost` when survival unavailable (D9, FR-022). |
| `proposal` | IntentToolProposal | The collapse suggestion (FR-021). |

**Rules**: overlapping/nested chains de-duplicated so content is not double-counted
(FR-023); ranked by `score` descending (FR-022).

---

## IntentToolProposal

| Field | Type | Notes |
|-------|------|-------|
| `suggested_name` | str | Derived from chain verbs/nouns (FR-021). |
| `inputs` | list | Inputs the single tool would take (chain's initial inputs). |
| `output` | str | The single output it would return (final step's shape). |
| `est_context_saved` | int | Estimated size saved per session by collapsing (sum of removed intermediates); labeled estimate. |

---

## ReportData (analysis → renderer contract)

Top-level object the renderer consumes; serialized shape defined in
`contracts/report-data.schema.json`.

| Field | Type | Notes |
|-------|------|-------|
| `generated_at` | str | ISO timestamp. |
| `scope` | object | `{sessions:int, from, to, aggregate:true}` + per-session drilldown index (FR-030). |
| `sizing` | object | `{unit, chars_per_token, method_notes, mcp_granularity}` (D6/D7/D7b disclosure). |
| `breakdown` | list[ContextBucket] | View 1 (main-thread window). |
| `sidechain` | object | `{size:int, calls:int}` — subagent/sidechain volume reported separately, excluded from `breakdown` (FR-014, D4). |
| `compaction` | object | `{events:int, pre_tokens:int, post_tokens:int, retention_pct:float?, exact:true}` — EXACT context-retention from `compactMetadata` (D8). |
| `heatmap` | list | View 2 cells: `{tool_key, call_count, total_size, survival?}`. |
| `chains` | list[Chain] | View 3, ranked. |
| `warnings` | list[str] | Explicit "no data" / "survival unavailable" notices (FR-010). |

**Rules**: any field derived from an estimate carries an `is_estimate`/`available` flag so
the renderer can label it (SC-004). The breakdown must satisfy SC-006 (buckets sum to total).

---

## Entity relationships

```text
Config ──drives──> discovery ──> SessionRef* ──parse──> ToolCall*
local Claude Code config ──read-only──> MountedTool* (incl. never-called, D7b)
ToolCall* + MountedTool* ──aggregate──> ContextBucket* (incl. per-tool ResidentEstimate)  (view 1)
ToolCall* (main thread) ──aggregate──> heatmap cells         (view 2)
ToolCall* (sidechain) ──aggregate──> ReportData.sidechain    (reported separately, D4)
ToolCall* ──mine──> Chain* ──has──> IntentToolProposal   (view 3)
CompactionEvent* (compactMetadata) ──> exact retention ratio (ReportData.compaction)
isCompactSummary text ──> SurvivalEstimate* ──shade──> heatmap cells & Chains
All ──> ReportData ──render──> dashboard.html
```
