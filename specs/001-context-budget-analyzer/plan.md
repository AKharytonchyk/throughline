# Implementation Plan: Throughline — Context Budget Analyzer

**Branch**: `001-context-budget-analyzer` | **Date**: 2026-07-15 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-context-budget-analyzer/spec.md`

**Note**: This plan is grounded in a read-only inspection of the real Claude Code data
layout on this machine (see [research.md](./research.md)); it does not guess at file
formats. No source files were modified during planning.

## Summary

Throughline is a local, single-user CLI that explains where a developer's Claude Code
context budget goes and finds recurring tool-call chains worth replacing with one
intent-based tool. It has two commands: `collect` (gather usage read-only into the tool's
own working directory) and `report` (produce a single self-contained HTML dashboard,
offline). An optional, consent-gated `hooks install` adds two passive Claude Code hooks
(`PostToolUse` logging, `PreCompact` transcript backup) so the essentialness signal can be
computed later.

Technical approach: pure Python standard library, **zero third-party dependencies**. The
parser flattens session transcript JSONL (`~/.claude/projects/**/*.jsonl`, path
configurable) into an ordered list of normalized tool calls with source attribution and
exact character/byte sizes. Analysis produces three views: a **main-thread** whole-window
context breakdown by source (built-in tools, MCP server/tool, per-tool resident schema
estimate, non-tool content incl. attachments, unattributed), a frequency×volume heatmap,
and a ranked list of data-dependent recurring chains with proposed intent tools and
estimated savings. The essentialness/survival signal is computed from the transcript
itself — comparing each tool's returned values against the post-compaction summary (the
`isCompactSummary` record after a `compact_boundary`); it works retroactively, is always
labeled an estimate, and is "unavailable" when nothing has compacted. `compactMetadata`
(pre/post token counts) also yields an **exact** context-retention figure, reported
alongside. The mounted-tool set (including never-called tools) comes from
`preCompactDiscoveredTools` when available (MCP **tool**-level) or local config otherwise
(MCP server-level); per-tool resident cost is a labeled heuristic estimate;
subagent/sidechain volume is reported separately from the main-thread total. The opt-in
`PreCompact` backup is optional insurance (no post-compact hook is needed). The dashboard
is a single self-contained HTML file — inline CSS + SVG + a little inline JS, no CDN, no
network.

## Technical Context

**Language/Version**: Python 3.11+ (verified available: 3.14.5). Standard library only.

**Primary Dependencies**: **None (standard library only).** Justification per constitution
Technology Constraints: the stdlib covers everything — e.g. `json`/`argparse`/`pathlib`/
`shutil` (parsing, CLI, config, safe copying), `html` + f-strings + hand-written inline SVG
(`math` for log scales) for rendering, `re` + set operations for value-overlap survival and
sequence mining (`hashlib` for chain ids), `dataclasses`/`datetime`, and `unittest` for
tests. No third-party runtime or test dependency.
Charting is hand-rolled inline SVG. Considered and rejected: Jinja2 (adds a dependency for
templating that f-strings already cover), Chart.js/D3 via CDN (violates
local-only — a CDN fetch is a network call), bundling a JS chart lib (a dependency to
justify and a larger surface than three static views need), tiktoken/anthropic tokenizer
(per-tool token counts are not needed — sizes are chars/bytes; an exact tokenizer would be
a dependency and the count-tokens API is a network call). See [research.md](./research.md).

**Storage**: Local files only, under the tool's own working directory (default
`~/.throughline/`, configurable): `config.json`, copied transcripts, the `PostToolUse`
call log (JSONL), `PreCompact` transcript backups, and the generated `dashboard.html`.
Nothing is written outside this directory except the opt-in hook entries the user installs
into `~/.claude/settings.json`.

**Testing**: `unittest` (standard library) against small synthetic fixture transcripts and
hook payloads. Parser, attribution, sizing, survival, sequence miner, and hooks-install
merge/uninstall are the priority test targets (per user direction). No test dependency
required; `pytest` may be used optionally by the developer but is not required to run the
suite.

**Target Platform**: Local developer machine, macOS/Linux, terminal + local browser. No
server, no container, no cloud.

**Project Type**: Single project — a CLI tool that emits a static HTML artifact.

**Performance Goals**: `report` completes in under 30 seconds (SC-008) for a typical
few-days dataset (~100+ sessions, tens of MB of JSONL observed on this machine).

**Constraints**: No network access during any operation (SC-005). All writes confined to
the working directory (FR-003); Claude Code files read-only via copy-before-parse (FR-002,
SC-007). The user's local Claude Code MCP configuration (e.g. `~/.claude.json`, project
`.mcp.json`) is read **read-only** to enumerate mounted servers (offline; individual MCP
tool enumeration is not available offline, so MCP mounted-but-unused is reported at server
level). Dashboard must be a single self-contained HTML file openable via `file://` (no CDN,
no external assets). Per-call and non-tool sizes/shares are exact (chars/bytes); per-tool
resident cost, survival rate, and projected savings are labeled estimates with stated
method (FR-006, FR-009, FR-025, SC-004).

**Scale/Scope**: One user, one machine. Order of ~100 sessions, tens of MB of transcripts;
must degrade gracefully on partial/in-progress transcripts and sessions with no tool
calls or no compaction.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution v1.1.0. Evaluated against all ten principles and the two constraint sections.

| Principle | Gate | Status |
|-----------|------|--------|
| I. Local-Only Operation | No sockets/HTTP/DNS in any code path; report opens via `file://`; verifiable with networking disabled (SC-005). | PASS |
| II. Privacy of Transcript Data | All derived data stays under the working directory; nothing transmitted (FR-003, FR-004). | PASS |
| III. Read-Only Toward Claude Code | Transcripts, settings, and MCP config are read **read-only** (transcripts copied before parsing; MCP config read for the mounted-tool set); never modified (FR-002, SC-007). The **only** write into Claude Code's domain is the opt-in hook install, which **merges** into existing `~/.claude/settings.json` (a `PostToolUse` hook already exists there), backs the file up first, and offers clean uninstall that removes only Throughline's entries. | PASS (sanctioned exception, consent-gated) |
| IV. Observer, Not Participant | `PostToolUse` only appends a log line; `PreCompact` only copies the transcript; both are passive, fast, non-blocking, and change no Claude Code output or decision. | PASS |
| V. Correctness Over Completeness | Per-call and non-tool sizes are exact (chars/bytes); the compaction-retention ratio is exact (from `compactMetadata`). Per-tool resident cost (disclosed heuristic), survival rate, and projected savings are labeled estimates with stated method; an explicit "unattributed" bucket keeps the breakdown complete; survival is "unavailable" when no compaction summary exists; MCP mounted-but-unused coverage is tool-level when discovered, else server-level, and labeled (FR-006/009/014/024/025/026). | PASS |
| VI. Simple to Run | Two commands: `throughline collect`, `throughline report`. Hooks are event-driven by Claude Code itself — Throughline runs no daemon (SC-003). | PASS |
| VII. Think Before Coding | Ambiguities resolved in spec clarifications; formats grounded in real data, not assumed; open estimation tradeoffs surfaced in research. | PASS |
| VIII. Simplicity First | Zero dependencies; inline SVG instead of a chart lib; flat module layout; no abstraction beyond the five named stages. | PASS |
| IX. Surgical Changes | Hook install touches only the `hooks` section of settings.json and preserves existing entries; uninstall is exact-reverse. | PASS |
| X. Goal-Driven Execution | Each user story has an independent test in quickstart.md tied to acceptance scenarios. | PASS |
| Technology Constraints | Python; standard library only; every candidate dependency justified and rejected above. | PASS |
| Development Workflow & Quality Gates | No network calls, no writes outside working dir, no Claude Code mutation beyond opt-in hooks, all estimates labeled, no unjustified dependency. | PASS |

**Result**: No violations. Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/001-context-budget-analyzer/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output — grounded technical decisions
├── data-model.md        # Phase 1 output — entities & normalized model
├── quickstart.md        # Phase 1 output — runnable validation per user story
├── contracts/           # Phase 1 output
│   ├── cli.md               # Command surface (collect/report/hooks/config)
│   ├── hooks.md             # Hook script I/O + settings.json merge contract
│   ├── transcript-schema.md # Input parsing contract (records the parser depends on)
│   └── report-data.schema.json  # analysis → renderer data contract
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
pyproject.toml                     # Metadata only; declares NO runtime dependencies
src/throughline/
├── __init__.py
├── __main__.py                    # enables `python -m throughline`
├── cli.py                         # argparse: collect, report, hooks, config
├── config.py                      # JSON config + working-dir paths + opt-in state
├── collector/
│   ├── __init__.py
│   ├── discover.py                # locate/list transcripts; copy-before-parse (read-only)
│   ├── hooks_install.py           # merge/uninstall hooks in settings.json (+backup, consent)
│   └── hook_scripts/
│       ├── post_tool_use.py       # standalone hook: append one call-log line
│       └── pre_compact.py         # standalone hook: fast, non-blocking transcript backup
├── parser/
│   ├── __init__.py
│   ├── transcript.py              # JSONL records → ordered ToolCall list
│   ├── attribution.py             # bucketing; CLI-wrapped-MCP re-attribution
│   └── mounted.py                 # mounted-tool set: built-in list + local MCP config (D7b)
├── analysis/
│   ├── __init__.py
│   ├── sizing.py                  # char/byte sizing; per-tool resident estimate; main-thread window totals
│   ├── breakdown.py               # context-by-source buckets (view 1)
│   ├── heatmap.py                 # frequency × volume (view 2)
│   ├── survival.py                # compaction pairing; survival estimate (view 2/3 shading)
│   └── sequences.py               # n-grams, data-dependency, fan-out, scoring, proposals (view 3)
└── report/
    ├── __init__.py
    ├── model.py                   # analysis → report-data (matches report-data.schema.json)
    ├── render.py                  # report-data → single self-contained HTML
    └── svg.py                     # inline SVG helpers (bars, heatmap grid)
tests/
├── fixtures/                      # small synthetic .jsonl transcripts + hook payloads
├── test_parser.py
├── test_attribution.py
├── test_sizing.py
├── test_survival.py
├── test_sequences.py
└── test_hooks_install.py
```

Runtime working directory (NOT in the repo), default `~/.throughline/`:

```text
~/.throughline/
├── config.json                    # transcript_dir, output_path, opt-in state, sizing method
├── transcripts/                   # read-only copies of session JSONL (copy-before-parse)
├── calls.log.jsonl                # PostToolUse append log
├── backups/precompact/            # PreCompact transcript snapshots
└── out/dashboard.html             # generated dashboard
```

**Structure Decision**: Single Python project (Option 1), organized by the five pipeline
stages from the spec and the user's suggested repo shape: `collector` → `parser` →
`analysis` → `report`, plus `config` and `cli`. This mirrors the build order (parser first,
miner last) and keeps each stage independently testable against fixtures. A user-level
working directory (`~/.throughline/`) is chosen over a project-local one because the tool
analyzes the user's Claude Code usage across all projects, not one repo.

## Complexity Tracking

> No constitution violations. No entries.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (none) | — | — |
