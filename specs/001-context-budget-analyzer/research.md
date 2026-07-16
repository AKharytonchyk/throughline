# Phase 0 Research: Throughline — Context Budget Analyzer

All decisions below were grounded in a **read-only** inspection of the real Claude Code
data on this machine (29 project dirs, 111 session transcripts, `~/.claude/settings.json`).
No Claude Code files were modified. Findings are cited as **[observed]** where taken from
that inspection and **[design]** where they are a design choice.

---

## D1. Language, runtime, and dependencies

**Decision**: Python (3.11+ floor; 3.14.5 present **[observed]**), **standard library
only, zero third-party runtime or test dependencies**.

**Rationale**: The constitution mandates Python and stdlib-first with written justification
for any dependency. Everything needed is in the stdlib: `json` (JSONL, config), `argparse`
(CLI), `pathlib`/`shutil` (discovery, copy-before-parse), `html` + f-strings (safe HTML),
hand-written inline SVG with `math` (log-scale charts), `re` + plain set operations
(value/CLI-wrap detection, survival overlap, n-grams), `hashlib` (chain ids),
`dataclasses`/`datetime`, and `unittest` (tests). Survival is set overlap of extracted
values — no `difflib` needed. Zero dependencies is the strongest possible fit for Local-Only and
Simplicity First.

**Alternatives considered**: Jinja2 (rejected — f-strings cover templating);
Chart.js/D3 via CDN (rejected — CDN load is a network call, violates Principle I);
bundling a JS chart library (rejected — a dependency to justify and heavier than three
static views need); tiktoken / Anthropic tokenizer (rejected — not required since amounts
are chars/bytes, and the accurate path is a network API call).

---

## D2. Transcript location, discovery, and copy-before-parse

**Decision**: Transcript directory is a **config value** defaulting to
`~/.claude/projects/` **[observed]**. Each project is a subdirectory whose name is the
project path with `/` replaced by `-` **[observed]**; each session is a `<uuid>.jsonl`
file **[observed]**. The tool **lists and selects** sessions (all, or filtered by
date/project); it never hardcodes a single path. Before parsing, each selected transcript
is **copied** into `~/.throughline/transcripts/` and only the copy is read.

**Rationale**: Satisfies FR-002 (read-only, copy-before-touch) and the user's explicit
"do not assume the on-disk path" direction. Discovery over a configurable root also
future-proofs against layout changes.

**Alternatives considered**: Hardcoding the observed path (rejected — brittle, violates
direction); parsing in place (rejected — copy-before-parse is a constitution requirement).

---

## D3. Transcript record schema the parser depends on

**Decision**: Parse defensively against this **[observed]** shape and ignore unknown
record types.

- Records are one JSON object per line with a top-level `type`. Observed types include:
  `user`, `assistant`, `system`, `attachment`, `file-history-snapshot`,
  `file-history-delta`, `mode`, `permission-mode`, `ai-title`, `last-prompt`,
  `queue-operation`, `pr-link`.
- `assistant` records carry `message.content`: a list of blocks of type `text`,
  `thinking`, or `tool_use`. A `tool_use` block has keys `{type, id, name, input, caller}`
  **[observed]**.
- Tool **results** appear two ways **[observed]**: as `tool_result` blocks
  `{type, tool_use_id, content, is_error}` inside a `user` record's `message.content`,
  **and** as a richer top-level `toolUseResult` on the same `user` record, linked via
  `sourceToolAssistantUUID`. The parser reads result **content** from the `tool_result`
  block (its `content` may be a string or a list of `{type:text,text}` blocks — handle
  both) and uses `toolUseResult` only if the block content is absent.
- `message.usage` carries `{input_tokens, output_tokens, cache_read_input_tokens,
  cache_creation_input_tokens, ...}` **[observed]** — exact per-request token totals, but
  **no per-tool breakdown**. This confirms the clarification that per-tool amounts must be
  measured as content size, not tokens.
- Ordering: use record array order within the file, tie-broken by `timestamp`
  **[observed present]**; pair each `tool_use.id` to its `tool_result.tool_use_id`.

**Rationale**: Grounds the parser in the actual format; defensive parsing satisfies the
partial/in-progress edge case (FR spec Edge Cases).

**Alternatives considered**: Relying solely on `toolUseResult` (rejected — the `tool_result`
block is the canonical content location and is always present for a completed call).

---

## D4. Subagent / sidechain handling

**Decision**: Records carry `isSidechain` and `parentUuid` **[observed]**, and `tool_use`
carries `caller` **[observed]**. The parser tags each tool call with `is_sidechain` and its
thread. **[design]** For v1, subagent (sidechain) tool calls are counted and attributed
like any other but **tagged**, so the breakdown can note them; they are *not* silently
merged into the main-thread window total in a way that hides them. The dashboard shows a
main-thread total and flags sidechain volume separately.

This is now a **spec requirement** (FR-014, clarified 2026-07-15): the breakdown
denominator is the main-thread window; sidechain volume is tagged and reported separately
and excluded from the main-thread total.

**Rationale**: Subagent calls run in their own context window; conflating them with the
main window would overstate the main-thread budget and mislead the "where does my context
go" view. Tagging keeps the number defensible (Principle V).

**Alternatives considered**: Ignoring sidechains (rejected — they are real context spend);
merging blindly (rejected — misattributes across windows).

---

## D5. Source attribution and CLI-wrapped MCP

**Decision**: **[design]**
- MCP tools are named `mcp__<server>__<tool>` → bucket = MCP, grouped by `<server>` then
  `<tool>`.
- Bare names (`Bash`, `Read`, `Grep`, `WebFetch`, `Task`, ...) → built-in bucket, each
  named separately.
- **CLI-wrapped MCP re-attribution**: for `Bash` calls, inspect the command string for an
  MCP-client invocation pattern (e.g. `mcpc`/`mcp` client calling `... tools-call
  @<server> <tool>` or `--server <server> --tool <tool>`). When matched, re-attribute that
  call's cost to the corresponding MCP `<server>/<tool>` bucket and mark
  `cli_wrapped_from = "Bash"`, so CLI-wrapped MCP traffic is not miscounted as Bash. The
  match is a conservative regex over known client patterns; unmatched Bash stays Bash.
- Anything unresolvable → the explicit **"unattributed"** bucket (FR-014).

**Rationale**: Directly implements FR-011 attribution and the user's flagged edge case
while keeping the heuristic conservative (Principle V — no over-claiming).

**Alternatives considered**: Deep-parsing arbitrary shell (rejected — unbounded and
error-prone; a targeted known-client regex is defensible and extensible).

---

## D6. Sizing unit and the whole-window denominator

**Decision**: **[design, per clarification]** The unit is **raw content size in characters
(default) or bytes** measured directly from content, so per-call and non-tool amounts and
shares are **exact**. Per bucket, size = sum of the sizes of the relevant content (tool_use
input + tool_result content for per-call; message/thinking text and attachments/files read
for non-tool; heuristic estimate for resident, D7). The **whole-window denominator** is the
**main-thread** context window (FR-012/FR-014, clarified 2026-07-15): the total distinct
content that entered that window over the session, each unit counted once — resident
overhead (D7) + all message/thinking text + tool inputs/outputs + **attachments/files
read**. Subagent/sidechain threads run in separate windows; their volume is tagged and
reported separately and is **excluded** from the main-thread denominator (D4). Shares are
size-shares of that main-thread total, labeled "by size", never as token shares.
`message.usage.input_tokens` is available and may be surfaced as an *exact* secondary
figure (labeled tokens) for a session-level sanity check, but it is not the primary unit.

**Rationale**: Implements FR-009/FR-012/FR-014 and the clarification (Q4 = raw size). Exact
sizes keep the headline numbers inside Principle V without a tokenizer dependency.

**Alternatives considered**: Tokens as the unit (rejected in clarification — needs a
tokenizer/network for accuracy); peak `input_tokens` as denominator (rejected as primary —
mixes units; kept as optional labeled cross-check).

---

## D7. Resident (schema) cost — per-tool heuristic estimate

**Decision**: **[design, per clarification 2026-07-15]** Resident overhead is reported
**per tool** as a **labeled ESTIMATE**, separated from per-call cost (FR-013). Principle V
is satisfied by labeling + a disclosed method — not by presenting a proxy as ground truth.

Method:
1. Measure total resident overhead **R** from the first assistant request's
   `cache_creation_input_tokens` **[observed available]** (the cached prefix = system
   prompt + all tool schemas), converted to the size unit via the disclosed
   `chars_per_token` factor (default ≈4).
2. Subtract an estimated system-prompt constant **S** to isolate schema overhead `R − S`;
   the system prompt is shown as its own resident line.
3. Distribute `R − S` across the mounted tool set (D7b) with per-tool heuristic weights
   `w_t` from a schema-size proxy (tool-name length + observed input-shape complexity):
   `resident_t = (R − S) × w_t / Σw`.
4. Every resident figure carries an "estimate" badge and states this method (FR-006,
   FR-009, FR-025).

**Rationale**: The user chose per-tool granularity; the constitution permits an
approximated metric provided it is labeled and its method stated. A transparent heuristic
that **normalizes to the measured total overhead** keeps the uncertainty confined to the
split, not the total.

**Alternatives considered**: Aggregate-only (rejected by clarification — per-tool wanted);
equal split (kept as the degenerate fallback when no input-shape proxy exists); fetching
live schemas (rejected — network, violates Principle I).

## D7b. Mounted-tool set (including never-called) — offline sources

**Decision**: **[design, grounded]** The mounted/available tool set is assembled from
**local, offline** sources (FR-006, FR-015), best source first:

1. **`preCompactDiscoveredTools`** (preferred) — a compaction boundary's `compactMetadata`
   carries the exact tool list Claude Code had discovered/mounted, at **MCP-tool**
   granularity (e.g. `mcp__server__tool`) **[observed on real data]**. When present, the
   mounted set is tool-level and mounted-but-unused is detectable per MCP tool.
2. **Built-in tools**: a known, maintained list (Bash, Read, Write, Edit, Glob, Grep,
   WebFetch, WebSearch, Task, …), version-labeled since it can drift between releases.
3. **MCP servers** (fallback, server granularity): read read-only from local config —
   `~/.claude.json` (`mcpServers`, `projects.<path>.mcpServers`) and project `.mcp.json`
   **[observed: `~/.claude.json` declares `acme-mcp`, `playwright`]** — for servers not
   already covered by discovered tools.
4. **Plugins**: `enabledPlugins` may contribute tools/skills; supplementary.

**Granularity**: with `preCompactDiscoveredTools` (any collected session that compacted),
MCP coverage is **tool-level**; without it, MCP falls back to **server-level** (a declared
server with zero observed calls is flagged unused). The active granularity is reported
(`sizing.mcp_granularity`) and labeled in the UI (FR-006).

**Rationale**: Grounds FR-015 in real offline sources rather than the transcript's
called-tools-only view. Reading config/metadata read-only respects Principle III.

**Alternatives considered**: Connecting to MCP servers to enumerate their tools (rejected —
network, Principle I); transcript-called-tools only (rejected — cannot reveal never-called
tools).

---

## D8. Essentialness / survival estimate

**Decision**: **[design, grounded — updated after inspecting real compacted transcripts]**
The transcript retains **both** sides of compaction on disk, so survival is computed from
the transcript itself — no hook or backup required, and it works **retroactively** on any
already-compacted session:

1. A `system` record with `subtype == "compact_boundary"` marks each compaction **[observed:
   e.g. one real session had 9 boundaries]** and carries `compactMetadata`
   (`preTokens`, `postTokens`, `preCompactDiscoveredTools`) **[observed]**.
2. The post-compaction **summary** is the `user` record flagged `isCompactSummary: true`
   that follows the boundary (a plain string) **[observed]**. The pre-compaction detail
   (tool outputs) remains earlier in the same append-only file.
3. Per-tool survival = fraction of a tool's distinctive returned values (the ids/paths the
   parser already extracts) that reappear in the summary; per-chain = mean over its steps.
   **Always labeled an ESTIMATE** with method (FR-025); **"unavailable"** when no session
   has a compaction summary (FR-026), never assumed.
4. **Exact companion metric**: `postTokens / preTokens` from `compactMetadata` gives an
   **exact** context-retention ratio (labeled exact, not estimate) surfaced alongside the
   per-tool estimate **[observed on real data: ~3% retained across 10 compactions]**.

The opt-in `PreCompact` backup (D10) is now **optional insurance** against transcript
rotation/truncation — survival no longer depends on it. A `SessionStart(compact)` /
"post-compact" hook was considered and **rejected as unnecessary**: the summary is already
persisted to disk.

**Rationale**: Uses data Claude Code already writes; retroactive; removes a hook dependency
(Simplicity First). Overlap over extracted identifiers is transparent and defensible; the
`compactMetadata` ratio is exact.

**Alternatives considered**: PreCompact-backup-only pairing (rejected — needs the hook and
can't run retroactively); a post-compact hook to capture the summary (rejected — redundant;
transcript already has it); LLM-judged relevance (rejected — network, non-deterministic).

---

## D9. Sequence miner (headline)

**Decision**: **[design]** From each session's ordered call list:
1. Build n-grams (n = 2..N, default N configurable, e.g. 6) of tool-call **signatures**
   (attributed identity), ignoring unrelated interleaved calls per FR-019 by also
   considering subsequences linked by data dependency.
2. Keep only sequences with a **data dependency**: a distinctive value (id/token/path)
   from step k's *output* reappears in step k+1's *input*. Coincidental adjacency is
   discarded. Value extraction is conservative (ids, quoted strings, paths, numbers over a
   length threshold) to avoid false links.
3. Detect **fan-out**: one call returns N items and is followed by ~N near-identical calls
   (same tool, inputs differing only by the per-item key). A fan-out counts as one logical
   step (FR-020) regardless of N.
4. Aggregate identical chain shapes **across sessions**; recurrence = count of occurrences
   (default "recurring" ≥ 2, configurable, per spec Assumptions).
5. Score = recurrence × total context cost × (1 − survival_rate); rank descending
   (FR-022). When survival is unavailable, score uses cost×recurrence and the card marks
   the essentialness factor as unavailable.
6. For the top chains, emit an **intent-tool proposal**: suggested name (derived from the
   chain's verbs/nouns), the inputs it would take (the chain's initial inputs), the single
   output it would return (the final step's shape), and estimated context saved per
   session (sum of intermediate payload sizes the collapse removes). Overlapping/nested
   chains are de-duplicated so content is not double-counted (FR-023).

**Rationale**: Implements US2 / FR-019–FR-023 and the user's miner spec directly. Keeping
data-dependency and fan-out as hard filters makes the headline output defensible rather
than a co-occurrence guess.

**Alternatives considered**: Pure frequent-sequence mining without data-dependency
(rejected — produces coincidental chains, low precision); graph/PrefixSpan libraries
(rejected — dependency; stdlib n-gram + dependency filter suffices at this scale).

---

## D10. Hooks integration (opt-in, merge, clean uninstall)

**Decision**: **[design, grounded]**
- `hooks install` (consent-gated) **merges** two entries into `~/.claude/settings.json`
  under `hooks` — **it must not overwrite**, because a `PostToolUse` hook already exists
  there **[observed]**. It backs up settings.json to `~/.throughline/backups/` before
  writing, appends Throughline's entries (tagged with a stable marker/id for later
  identification), and writes atomically.
  - `PostToolUse`: runs `hook_scripts/post_tool_use.py`, which reads the event JSON on
    stdin (`session_id`, `tool_name`, `tool_input`, `tool_output`, plus timing) and appends
    one line to `~/.throughline/calls.log.jsonl` with `tool_name`, `tool_input` (or its
    size), `tool_output` size, `timestamp`, `session_id`. Logs only; never blocks.
  - `PreCompact`: runs `hook_scripts/pre_compact.py`, which reads `session_id`,
    `transcript_path`, `cwd` on stdin and copies `transcript_path` into
    `~/.throughline/backups/precompact/`. Trigger + copy only; fast and non-blocking.
    **Optional insurance only** — the transcript retains pre-compaction detail on disk, so
    the survival signal (D8) does not depend on this backup; it guards against transcript
    rotation/truncation.
- `hooks uninstall` removes **only** Throughline's tagged entries, restoring the prior
  shape; `hooks status` reports installed/opt-in state.
- Hook scripts are standalone files under the tool's own directory and write user data only
  within `~/.throughline/`.

**Rationale**: This is the single sanctioned write into Claude Code's domain (Principles
III/IV). Merge+backup+tagged-uninstall makes it surgical (Principle IX) and reversible;
passive log/copy keeps it observer-only (Principle IV). Grounded by the observed
pre-existing hook.

**Alternatives considered**: Writing to `settings.local.json` (rejected — observed to hold
only permissions and is project-scoped; user-level settings.json captures across all
projects); overwriting the `hooks` block (rejected — destroys the user's existing hook,
violates Principle III/IX).

---

## D11. Configuration and opt-in state

**Decision**: **[design]** A single `~/.throughline/config.json` (stdlib `json`) holds:
`transcript_dir` (default `~/.claude/projects`), `working_dir`, `output_path`, `size_unit`
("chars"|"bytes"), `chars_per_token` (for the resident estimate), `min_recurrence`, and
`hooks_opt_in` state. `throughline config` prints/edits it. No secrets, no network config.

**Rationale**: JSON matches Claude Code's own config idiom and needs no dependency; keeps
all knobs (including the disclosed estimation factor) explicit and inspectable.

**Alternatives considered**: TOML via `tomllib` (fine, but read-only in stdlib; JSON is
read/write in stdlib and matches the ecosystem).

---

## D12. Dashboard rendering

**Decision**: **[design]** `report` renders one **self-contained** `dashboard.html`:
inline CSS, hand-generated inline **SVG** for the breakdown bars, the frequency×volume
heatmap grid (with essentialness shading), and the ranked sequential-pattern cards. No
`<script src>`, no CDN, no external fonts — opens via `file://` with no network and no
server. A trivial `python -m http.server` is documented as an optional convenience only.
Every estimated figure (resident cost, survival rate, projected savings) carries a visible
"estimate" badge and a tooltip/footnote stating its method; missing data (no sessions, no
compaction) is stated explicitly.

**Rationale**: Implements FR-008/FR-009/FR-010/SC-004/SC-005 and the user's single-file
requirement with zero dependencies.

**Alternatives considered**: A live web app / local server as the primary view (rejected —
adds a process to babysit, against Principle VI and the "no server required" direction).

---

## Resolved unknowns

All Technical Context items are resolved; **no `NEEDS CLARIFICATION` remain**. The genuine
data-limitation tradeoffs — per-tool resident cost is a disclosed heuristic estimate (D7),
MCP mounted-but-unused detection is at server granularity (D7b), and survival requires the
opt-in backup (D8/D10) — are handled by labeling estimates, stating their methods, and
reporting "unavailable" rather than guessing, consistent with Principle V.
