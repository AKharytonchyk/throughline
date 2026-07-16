# Feature Specification: Throughline — Context Budget Analyzer

**Feature Branch**: `001-context-budget-analyzer`

**Created**: 2026-07-15

**Status**: Draft

**Input**: User description: "Build throughline, a personal, local tool that shows a single developer where their Claude Code context budget actually goes, so they can see which tools and data are worth their context cost — and ultimately design better, intent-based MCP tools instead of thin API proxies."

## Clarifications

### Session 2026-07-15

- Q: What defines two tool-call sequences as the same recurring chain (US2 detection)? → A: The same ordered sequence of tool identities (server-qualified names) linked by output→input data dependency between consecutive steps; unrelated calls interleaved between steps are ignored (they don't break the match); a fan-out step counts as one logical step regardless of item count.
- Q: The "share of total" percentages in the context breakdown are a share of what total? → A: The whole context window — all ingested content, including non-tool content (user/assistant messages, files read) shown as its own aggregate bucket.
- Q: Should the breakdown and heatmap aggregate across all collected sessions or per session? → A: Aggregate across all collected sessions by default, with the ability to drill into a single session.
- Q: Are per-tool/per-bucket amounts measured in tokens or raw size? → A: Raw content size in characters/bytes (exact measurement), avoiding token estimation; the only estimates are per-tool resident (schema) cost, the essentialness/survival signal, and projected chain savings.
- Q: How should resident (schema) cost be reported given schema text isn't available offline (FR-006)? → A: Per-tool, via a documented heuristic, and always presented as a labeled estimate with its method stated — never as an exact/ground-truth figure.
- Q: How is the set of mounted-but-never-called tools determined (FR-015)? → A: From local offline sources — the known built-in tool list plus the MCP servers declared in the user's local Claude Code configuration; where individual MCP tools can't be enumerated offline, coverage may be at the server level and is labeled as such.
- Q: What counts toward the whole-window total and how are subagent/sidechain threads handled (FR-012/014)? → A: The denominator is the main-thread context window, counting all ingested content once (messages, thinking, tool inputs/outputs, resident schemas, and attachments/files read); subagent/sidechain volume is tagged and reported separately, never folded into the main-thread total.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See where my context budget goes (Priority: P1)

A developer has been using Claude Code for their work. They want to know, in plain
numbers, which tools and which resident tool schemas are consuming their context
window — "where does my money go" for the context budget — so they can unmount dead
weight they never use.

**Why this priority**: This is the foundational value of the tool and the simplest
complete slice. On its own it lets the user answer success outcome (a): naming the
mounted tools/servers whose context cost they don't use. It also establishes the
context-cost accounting that later stories build on.

**Independent Test**: Collect a few real sessions with one command, open the dashboard
with one command, and confirm the user can read a breakdown of context spend by source,
with resident (schema) cost separated from per-call (result) cost, and can identify at
least one mounted-but-never-called tool.

**Acceptance Scenarios**:

1. **Given** collected data aggregated across one or more sessions, **When** the user
   opens the dashboard, **Then** they see a breakdown that attributes ingested content to
   buckets — each built-in tool named separately, MCP tools grouped by server then tool,
   mounted tool schemas as resident cost, and a "non-tool content" bucket for everything
   else in the window — with per-bucket amount, frequency, and share of the whole
   main-thread context window; **And** they can drill into any single session.
2. **Given** the breakdown, **When** the user looks at any bucket, **Then** resident
   (one-time schema) cost is shown distinctly from per-call (result) cost.
3. **Given** a tool that was mounted but never invoked, **When** the user views the
   breakdown, **Then** that tool appears with its resident cost and zero calls, flagged
   as an unmount candidate.
4. **Given** content that cannot be attributed to a specific tool, **When** the
   breakdown is shown, **Then** it appears in an explicit "unattributed" bucket rather
   than being dropped, so the buckets sum to the whole.

---

### User Story 2 - Find tool chains worth collapsing into one intent tool (Priority: P2)

The developer repeatedly runs the same multi-step tool dance (for example: get sprint →
get team → get stories → get status of each story), where each step feeds the next and
the last fans out into one call per item. They want the tool to surface these recurring
chains, quantify what they cost, and propose a single intent-based tool that would
replace each one — ranked so they know which two or three to build first.

**Why this priority**: This is the headline feature and delivers success outcome (b).
It depends on the context-cost accounting from User Story 1, so it follows P1.

**Independent Test**: With several sessions collected that contain a repeated,
data-dependent tool sequence, open the dashboard and confirm the recurring chain is
detected, shows its recurrence count and total context cost, includes a proposed
intent-tool (name plus inputs/outputs), and that chains are ranked by estimated context
saved.

**Acceptance Scenarios**:

1. **Given** multiple sessions containing the same ordered, data-dependent tool
   sequence (even when unrelated calls are interleaved between its steps), **When** the
   user opens the dashboard, **Then** that sequence is listed as a recurring chain with
   the number of times it recurs.
2. **Given** a chain whose final step runs once per item produced by an earlier step,
   **When** it is displayed, **Then** the fan-out is recognized and reflected in the
   chain's total context cost.
3. **Given** a detected chain, **When** the user inspects it, **Then** they see its
   total context cost, the portion that was intermediate data that never proved
   essential (labeled as an estimate), and a proposed single intent-based tool with a
   suggested name and the inputs/outputs it would need.
4. **Given** several detected chains, **When** the user views the list, **Then** chains
   are ranked by the estimated context a collapse would save, highest first, so the top
   2-3 candidates are immediately visible.

---

### User Story 3 - Spot expensive tools at a glance (Priority: P3)

The developer wants a single visual that shows every tool they actually invoked by how
often it was called and how much content it returned, so the expensive tools jump out
and the prime redesign candidates (called often, returning large, mostly-noise results)
are obvious.

**Why this priority**: It sharpens targeting for redesign but is an enrichment on top of
the accounting (P1) and the chains (P2); useful independently but lower urgency than the
two success outcomes.

**Independent Test**: With collected data, open the dashboard and confirm every invoked
tool is placed on frequency and volume axes, with high-frequency/high-volume tools
visually distinguished from rarely-called or small-result tools.

**Acceptance Scenarios**:

1. **Given** collected data with tool calls, **When** the user opens the heatmap,
   **Then** every tool they invoked is positioned by call frequency and total returned
   volume.
2. **Given** the heatmap, **When** the user scans it, **Then** tools that are both
   high-frequency and high-volume are visually distinguishable from cheap ones.
3. **Given** that the essentialness signal is available for a tool, **When** the tool is
   shown on the heatmap, **Then** the estimated essential-vs-noise split is indicated and
   labeled as an estimate; **When** it is not available, **Then** the tool still appears
   on both axes without a fabricated split.

---

### User Story 4 - Estimate how much returned content actually mattered (Priority: P4)

The developer wants to know how much of what each tool (and each chain) pulled into
context actually mattered, approximated by how much of it survives Claude Code's context
compaction. Content that was ingested but did not survive into the compacted summary was
largely noise for that intent.

**Why this priority**: It is the most technically involved signal and is explicitly an
estimate; it enriches User Stories 2 and 3 rather than standing alone as a headline. It
is sequenced last so the earlier stories deliver value first and degrade gracefully
without it.

**Independent Test**: With at least one session that underwent compaction and for which
pre-compaction detail was captured, open the dashboard and confirm a per-tool survival
rate is shown, clearly labeled as an estimate with its method stated; and that a session
which never compacted reports the estimate as unavailable rather than guessing.

**Acceptance Scenarios**:

1. **Given** captured pre-compaction content and the corresponding post-compaction
   summary, **When** the dashboard is generated, **Then** each tool shows an estimated
   survival rate (fraction of returned content surviving compaction), labeled as an
   estimate with its method stated.
2. **Given** a chain, **When** essentialness is available, **Then** the chain's
   never-essential intermediate-data portion (used in User Story 2) is derived from the
   survival estimate and labeled as an estimate.
3. **Given** data for which no compaction has occurred, **When** the dashboard is
   generated, **Then** the survival estimate is reported as unavailable, not assumed.

---

### Edge Cases

- **No data yet**: With no sessions collected, the dashboard states there is nothing to
  show and how to collect, rather than rendering empty or misleading charts.
- **Session with no tool calls**: Appears with resident schema cost but no per-call
  cost, without errors.
- **Never compacted**: Essentialness/survival is reported as unavailable everywhere it
  would otherwise appear.
- **Mounted-but-unused tools**: Always surfaced as resident cost with zero calls (the
  prime unmount candidates), never hidden.
- **Very large single result**: Represented at true size in volume; not truncated in a
  way that hides its context cost.
- **Fan-out with variable count**: A chain whose fan-out step count differs run-to-run is
  still recognized as the same recurring chain.
- **Overlapping / nested chains**: Handled without double-counting the same content
  across reported chains.
- **In-progress or partially written session data**: Read safely as read-only; partial
  data does not corrupt the analysis or the source.
- **MCP server disconnected or tool renamed mid-session**: Attributed as encountered;
  unresolved identities fall into the explicit unattributed bucket.
- **Unattributable content**: Shown in the explicit "unattributed" bucket so totals
  remain complete.
- **Subagent/sidechain threads**: Tool calls made in subagent (sidechain) threads run in
  separate context windows; they are tagged and reported separately, never merged into the
  main-thread window total.

## Requirements *(mandatory)*

### Functional Requirements

**Collection**

- **FR-001**: The tool MUST provide a single command that collects Claude Code usage
  data for later analysis, without requiring a persistent background daemon.
- **FR-002**: Collection MUST treat all Claude Code files (transcripts, configuration,
  session state) as read-only inputs and MUST NOT modify, delete, truncate, or corrupt
  them; data MUST be copied into the tool's own working directory before processing.
- **FR-003**: The tool MUST store all collected and derived data only within its own
  working directory, and MUST NOT write Claude Code-derived data anywhere else.
- **FR-004**: The tool MUST NOT transmit any collected data off the machine and MUST
  operate without any network access during collection or viewing.
- **FR-005**: Collection MUST capture, per tool call: the tool identity (built-in tool
  name, or MCP server plus tool name), the call inputs, the returned result content, the
  size of that content, a timestamp, and the call's order within its session.
- **FR-006**: The tool MUST determine the set of mounted/available tools — including
  tools that were never called — from local, offline sources: the known set of built-in
  tools plus the MCP servers declared in the user's local Claude Code configuration. Where
  individual MCP tools cannot be enumerated offline, coverage MAY be at the server level
  and MUST be labeled as such. The tool MUST estimate each tool's resident (schema) size
  via a documented heuristic and MUST present these per-tool resident sizes as estimates
  with the method stated (exact schema text is not available offline).
- **FR-007**: To support the essentialness signal, the tool MUST have access to both the
  pre-compaction tool-result content and the corresponding post-compaction summary. The
  session transcript on disk retains both (the pre-compaction detail persists in the
  append-only file; the summary is the compaction-summary record), so the tool reads them
  from the transcript. A pre-compaction backup MAY be captured via an opt-in logging hook
  as insurance against transcript loss; any such hook MUST be opt-in and MUST NOT otherwise
  alter how Claude Code behaves.

**Analysis & dashboard (general)**

- **FR-008**: The tool MUST provide a single command that produces a locally-viewable
  dashboard from the collected data, with no network service required to view it.
- **FR-009**: Context amounts MUST be expressed as raw content size in a single
  consistent unit (characters, or bytes) measured directly from the content. Per-call and
  non-tool content sizes are exact measurements and MUST NOT be labeled or presented as
  token counts. Figures that ARE approximations — per-tool resident (schema) cost, the
  essentialness/survival estimate, and projected chain savings — MUST be explicitly
  labeled as estimates and MUST state the method used to derive them; the tool MUST NOT
  present a proxy value as ground truth.
- **FR-010**: When data required for a view is missing (e.g., no sessions collected, no
  compaction observed), the dashboard MUST state the absence explicitly rather than omit
  it silently or fabricate values.
- **FR-030**: The context breakdown and tool heatmap MUST aggregate across all collected
  sessions by default and MUST allow the user to drill into a single session. Resident
  schema cost (which varies per session) MUST be aggregated in a clearly stated way (e.g.,
  summed per-session footprints) when shown in the combined view.

**Where does my context go (User Story 1)**

- **FR-011**: The dashboard MUST present a breakdown of context spend across the whole
  main-thread context window, attributing every piece of ingested content to a bucket: each built-in
  tool named separately; MCP tools grouped by server then by tool; mounted tool schemas
  as resident cost; and all non-tool content (e.g., user/assistant messages and files
  read) as an aggregate "non-tool content" bucket.
- **FR-012**: For each bucket the breakdown MUST show the amount of content pulled in,
  the frequency (how often it occurred), and its share of the whole main-thread context
  window (all ingested content, counted once; see FR-014).
- **FR-013**: The breakdown MUST separate RESIDENT/one-time cost (mounted schemas
  present across a session) from PER-CALL cost (content returned by actual tool calls),
  presenting the two distinctly because they have different fixes (unmount vs.
  consolidate).
- **FR-014**: The breakdown MUST account for the whole main-thread context window: every
  unit of ingested content — messages, thinking, tool inputs/outputs, resident schemas,
  and attachments/files read — MUST land in exactly one bucket (a tool, resident schemas,
  non-tool content, or an explicit "unattributed" bucket), counted once, so the buckets
  sum to the total main-thread window size. Content from subagent/sidechain threads MUST
  be tagged and reported separately and MUST NOT be folded into the main-thread total
  (their separate context windows would otherwise inflate it).
- **FR-015**: Tools that were mounted but never invoked MUST be identifiable in the
  breakdown (resident cost, zero calls) as unmount candidates.

**Tool heatmap (User Story 3)**

- **FR-016**: The dashboard MUST present every tool the user actually invoked positioned
  on two axes: call frequency and total volume of content returned.
- **FR-017**: The heatmap MUST make high-cost tools (high frequency and high volume)
  visually distinguishable from low-cost ones.
- **FR-018**: Where the essentialness signal is available, the heatmap MUST additionally
  indicate the estimated essential-vs-noise split for each tool, labeled as an estimate;
  where it is not available, the tool MUST still appear on both axes without a fabricated
  split.

**Sequential patterns (User Story 2)**

- **FR-019**: The tool MUST detect recurring chains of tool calls, where a chain is the
  same ordered sequence of tool identities (a built-in tool name, or a server-qualified
  MCP tool name) linked by output→input data dependency between consecutive steps.
  Unrelated tool calls interleaved between a chain's steps MUST be ignored (they do not
  break the match), and the chain MUST be recognized across the user's sessions.
- **FR-020**: Chain detection MUST recognize fan-out steps, where one step runs once per
  item produced by a previous step. A fan-out step MUST count as a single logical step in
  the chain regardless of how many items it iterates over, and a chain MUST be recognized
  as the same recurring chain even when the fan-out count varies between runs.
- **FR-021**: For each detected chain the dashboard MUST show: how often it recurs; its
  total context cost; the portion of that cost that is intermediate data which never
  proved essential (labeled as an estimate); and a proposed single intent-based tool that
  would collapse the chain, including a suggested name and the inputs/outputs it would
  need.
- **FR-022**: Detected chains MUST be ranked by the estimated amount of context a
  collapse would save, highest first, so the top 2-3 candidates are immediately visible.
- **FR-023**: Reported chains MUST NOT double-count the same content when chains overlap
  or nest.

**Essentialness signal (User Story 4)**

- **FR-024**: The tool MUST estimate, per tool and per chain, a survival rate: the
  fraction of returned content that survives Claude Code's context compaction, derived by
  comparing pre-compaction content against the post-compaction summary. Where Claude Code
  records an exact context-retention figure at compaction (pre/post token counts), the tool
  MAY additionally report that as an exact companion metric, clearly distinguished from the
  per-tool estimate.
- **FR-025**: The survival rate and every figure derived from it MUST be presented
  explicitly as an ESTIMATE, with its method stated, wherever it is shown (the exact
  retention figure of FR-024 is labeled exact, not estimate).
- **FR-026**: When no compaction has occurred for the relevant data, the tool MUST
  report the survival estimate as unavailable rather than assume a value.

**Scope guards**

- **FR-027**: The tool MUST operate for a single user on a single machine and MUST NOT
  provide multi-user, sharing, authentication, server, or cloud features.
- **FR-028**: In this version the tool MUST analyze only Claude Code sessions (no other
  agents).
- **FR-029**: The tool MUST NOT implement the suggested intent-based tools, route or
  proxy MCP traffic, or change Claude Code behavior beyond the opt-in logging of FR-007.

### Key Entities *(include if feature involves data)*

- **Session**: One Claude Code working session that was analyzed; has a time span and
  the project it ran in, and contains the requests, tool calls, and any compaction
  events observed.
- **Tool**: An available capability, either a built-in tool (named individually) or an
  MCP tool (belonging to a server); has a schema with a measurable resident size and a
  mounted/never-called status.
- **Tool Call**: A single invocation instance of a tool — its inputs, returned content,
  content size, timestamp, and position/order within a session.
- **Context Bucket**: An attribution category for ingested content (a specific built-in
  tool, an MCP server/tool, resident schemas, non-tool content, or "unattributed");
  carries amount pulled in (content size), frequency, and share of the whole main-thread
  context window.
- **Tool Chain (Pattern)**: An ordered, recurring, data-dependent sequence of tool calls
  (optionally with a fan-out step); carries recurrence count, total context cost, an
  estimated never-essential portion, and a ranking by estimated savings.
- **Intent Tool Proposal**: A suggested single tool that would collapse a chain — a
  proposed name and the inputs/outputs it would need — with an estimated context saving.
- **Compaction Event**: A point where Claude Code summarized the conversation; pairs the
  captured pre-compaction content with the post-compaction summary.
- **Survival Estimate**: A per-tool or per-chain estimated fraction of returned content
  that survived compaction; always labeled as an estimate, or marked unavailable.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After a few days of normal Claude Code use (several sessions with tool
  activity), a user opening the dashboard can, within 5 minutes and without external
  help, name the mounted tools or servers whose resident context cost they never used
  (zero calls). *(Success outcome a)*
- **SC-002**: The dashboard surfaces the top 2-3 recurring tool chains ranked by
  estimated context saved, each with a proposed intent-based tool and an estimated
  saving. *(Success outcome b)*
- **SC-003**: Collecting data is a single command and viewing the dashboard is a single
  command; neither requires a long-running background process the user must start or
  monitor.
- **SC-004**: Amount and share figures are exact measured content sizes (in
  characters/bytes), not estimates; every remaining figure that IS an approximation (the
  survival rate and projected chain savings) carries a visible "estimate" label and a
  stated method, and no approximated value is presented as exact.
- **SC-005**: During both collection and viewing, the tool makes zero network
  connections, verifiable by running with networking disabled.
- **SC-006**: The context breakdown is complete: every unit of ingested content in the
  main-thread context window lands in exactly one bucket (a tool, resident schemas,
  non-tool content, or an explicit "unattributed" bucket), and the buckets sum to the
  measured total main-thread window size.
- **SC-007**: After a collection run, Claude Code's transcripts, configuration, and
  session state are byte-for-byte unchanged (except for opt-in logging the user
  explicitly enabled).
- **SC-008**: For a typical few-days dataset, the dashboard is produced within a time
  short enough for interactive use (target: under 30 seconds) on the user's own machine.

## Assumptions

- Collection's primary data source is the Claude Code session data already written to
  the user's machine; existing sessions can be analyzed retroactively where the needed
  detail is present in that data.
- Pre-compaction content for the essentialness signal is captured going forward — from
  the session data if it retains that detail, otherwise via opt-in passive logging the
  user enables. Sessions for which it was never captured show essentialness as
  unavailable rather than estimated.
- Context amounts are measured as raw content size in characters (or bytes), read
  directly from the content, so amounts and shares are exact; tokens are deliberately not
  used as the unit, to avoid estimation. Shares are size-based shares of the whole context
  window and are presented as such (size), not as token shares.
- Resident schema cost is treated as a standing footprint present throughout a session
  (counted once per session), reported separately from cumulative per-call result volume,
  with both expressed in the same size unit so they can be compared honestly.
- A chain is considered "recurring" when the same ordered, data-dependent sequence is
  observed at least twice across the analyzed sessions; this threshold is a reasonable
  default and may be adjustable.
- MCP tools are attributed to their server via the tool's identity (e.g., a
  server-qualified tool name).
- "A few days of normal use" implies at least several sessions containing tool activity
  are available before the rankings become actionable.
- Latency of the analyzed tools is explicitly out of scope; the concern the tool exists
  to surface is context volume, not speed.

## Dependencies

- Requires read access to the user's local Claude Code session data on the same machine.
- The essentialness signal depends on either the session data retaining pre-compaction
  detail or the user enabling opt-in logging to capture it before compaction discards it.
