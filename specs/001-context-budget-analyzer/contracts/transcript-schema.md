# Contract: Transcript Parsing (Input)

The subset of the Claude Code session-transcript JSONL format the parser depends on. Based
on a read-only inspection of real transcripts on this machine (see research.md D3). The
parser MUST be **defensive**: tolerate missing/extra fields, unknown record types, and
partial final lines (in-progress sessions), and never crash the whole run on one bad line.

## File

- One JSON object per line (`.jsonl`) at `<transcript_dir>/<project-dir>/<session-uuid>.jsonl`.
- `<project-dir>` = project path with `/` → `-`. `<session-uuid>` = `session_id`.

## Records consumed

| `type` | Fields used | Purpose |
|--------|-------------|---------|
| `assistant` | `message.content[]`, `message.usage`, `timestamp`, `uuid`, `isSidechain` | Tool calls, token usage, ordering, thread. |
| `user` | `message.content[]`, `toolUseResult`, `isCompactSummary`, `timestamp` | Tool results; user/non-tool size; **`isCompactSummary: true` string content = the post-compaction summary (survival POST side, D8)**. |
| `system` | `subtype`, `compactMetadata` | `subtype == "compact_boundary"` marks compaction; `compactMetadata` carries `preTokens`, `postTokens` (exact retention) and `preCompactDiscoveredTools` (real mounted set, D7b/D8). |

`attachment` records represent ingested content (files read / pasted context); **their
sizes count toward the `non_tool` bucket** of the main-thread window total (FR-014). Other
observed types (`file-history-snapshot`, `file-history-delta`, `mode`, `permission-mode`,
`ai-title`, `last-prompt`, `queue-operation`, `pr-link`) are bookkeeping and are ignored for
context accounting.

**The mounted-tool set** is NOT the transcript's called-tools view. Preferred source is
`compactMetadata.preCompactDiscoveredTools` (the real mounted list, MCP **tool**-level);
fallback is local Claude Code config — a known built-in list plus MCP servers in
`~/.claude.json` / project `.mcp.json` (MCP **server**-level). See research.md D7b, FR-006.

**Compaction retains both sides on disk**: pre-compaction detail stays earlier in the
append-only file; the summary is the `isCompactSummary` record. So survival is computed
from the transcript directly (D8) — the PreCompact backup is optional insurance only.

## Content blocks (`message.content[]`)

| Block `type` | Fields used |
|--------------|-------------|
| `tool_use` | `id`, `name`, `input`, `caller` |
| `tool_result` | `tool_use_id`, `content` (string **or** list of `{type:"text",text}`), `is_error` |
| `text` | `text` (counts toward non-tool content) |
| `thinking` | `thinking`/`text` (counts toward non-tool content) |

## Pairing & ordering rules

1. Order records by file position; use `timestamp` only to break ties.
2. Pair `tool_use.id` ⇄ `tool_result.tool_use_id`. A `tool_use` with no matching result
   (in-progress/interrupted) is still counted with `output_size = 0` and flagged.
3. `tool_result.content`: if a string, size = len(string); if a list, size = sum of block
   text sizes. Fall back to `toolUseResult` only when the block content is absent.
4. `message.usage.cache_creation_input_tokens` of the **first** assistant request seeds the
   resident estimate (research.md D7).
5. `isSidechain == true` ⇒ tag the call `is_sidechain` (research.md D4).

## Attribution rules (see research.md D5)

- `name` matching `^mcp__(?P<server>[^_]+(?:_[^_]+)*)__(?P<tool>.+)$` ⇒ MCP bucket.
- Bare `name` ⇒ built-in bucket, named individually.
- `Bash` whose command matches a known MCP-client wrapper pattern ⇒ re-attribute to the
  named MCP `server/tool`, set `cli_wrapped_from="Bash"`.
- Anything unresolved ⇒ `unattributed` bucket.

## Failure handling

- Malformed line ⇒ skip that line, continue, count it in a `parse_warnings` tally.
- Empty/zero-session input ⇒ produce an empty result that the report renders as an explicit
  "no data" state (FR-010), not an error.
