---
description: "Task list for Throughline — Context Budget Analyzer"
---

# Tasks: Throughline — Context Budget Analyzer

**Input**: Design documents from `/specs/001-context-budget-analyzer/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: INCLUDED. The plan explicitly requests tests for the parser and sequence miner
(and lists attribution, sizing, survival, mounted-set, and hooks-install as targets). Test
tasks use the standard-library `unittest` framework against small fixture transcripts. Per
Constitution Principle X, write the parser and sequence-miner tests before/alongside the
code they cover.

**Organization**: Tasks are grouped by user story. Story phases are sequenced by the plan's
explicit **build order** (dependency-driven), not strict P-number order — see "Dependencies
& Execution Order".

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1 / US2 / US3 / US4 (from spec.md); Setup/Foundational/Polish have no label
- All paths are repo-relative; source under `src/throughline/`, tests under `tests/`

## Path Conventions

- Single Python project. Runtime data lives OUTSIDE the repo, under `~/.throughline/`.
- **Zero third-party dependencies** (constitution Technology Constraints); `unittest` for tests.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project skeleton with no runtime dependencies.

- [x] T001 Create the project structure per plan.md (`src/throughline/{collector,parser,analysis,report}/`, `src/throughline/collector/hook_scripts/`, `tests/fixtures/`, `__init__.py` files)
- [x] T002 Create `pyproject.toml` with package metadata and a `throughline` console-script entry point; declare **no runtime dependencies** (record the stdlib-only justification per constitution)
- [x] T003 [P] Implement `src/throughline/config.py`: load/save `~/.throughline/config.json` per data-model.md (transcript_dir, working_dir, output_path, size_unit, chars_per_token, min_recurrence, max_ngram, mcp_config_paths [default `~/.claude.json` + project `.mcp.json`], hooks_opt_in); refuse paths outside working_dir
- [x] T004 [P] Implement CLI skeleton `src/throughline/cli.py` + `src/throughline/__main__.py`: argparse subcommands `collect`, `report`, `hooks {install,uninstall,status}`, `config` per contracts/cli.md (wiring only), with documented exit codes
- [x] T005 [P] Create fixtures in `tests/fixtures/`: tiny synthetic `.jsonl` transcripts including (a) a data-dependent chain with a fan-out step, (b) a **built-in tool never called** and (c) a **declared-but-unused MCP server**, (d) a `system`/`compact_boundary` record with pre/post content, (e) a CLI-wrapped MCP `Bash` call, (f) an `attachment` record, (g) a `isSidechain` subagent thread; plus a sample MCP config (`mcpServers`) and PostToolUse/PreCompact stdin payloads

**Checkpoint**: Package imports, `throughline --help` lists all commands.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The discover→parse→mounted-set→size→model→render pipeline every story depends on.

**⚠️ CRITICAL**: No user story can be completed until this phase is done.

- [x] T006 [P] Implement `src/throughline/collector/discover.py`: locate/list sessions under `transcript_dir`, filter by date/project, **copy-before-parse** into `~/.throughline/transcripts/` (read-only on source) per contracts/transcript-schema.md and research.md D2 (FR-002, FR-003)
- [x] T007 [P] Implement `src/throughline/parser/transcript.py`: parse JSONL defensively into an ordered `ToolCall` list (pair `tool_use`↔`tool_result`, handle string/list result content, tag `is_sidechain`, tolerate malformed lines); capture non-tool content sizes (message/thinking text and `attachment` records); and capture compaction data — `compact_boundary` `compactMetadata` (pre/post tokens, `preCompactDiscoveredTools`) and the `isCompactSummary` summary text — per contracts/transcript-schema.md and data-model.md (FR-005, FR-007)
- [x] T008 Implement `src/throughline/parser/attribution.py`: bucket calls (`builtin` / `mcp` server+tool / `unattributed`) and re-attribute CLI-wrapped MCP `Bash` calls to their MCP bucket per research.md D5 (FR-011, FR-014) — depends on T007
- [x] T009 [P] Implement `src/throughline/parser/mounted.py`: assemble the mounted-tool set including never-called tools from **local, offline** sources — `preCompactDiscoveredTools` when available (MCP **tool**-level, preferred), a maintained built-in list, and MCP servers from `mcp_config_paths` (`~/.claude.json`/project `.mcp.json`) as **server**-level fallback; the active granularity is reported and labeled, per research.md D7b (FR-006, FR-015)
- [x] T010 Implement `src/throughline/analysis/sizing.py`: exact char/byte sizes for per-call and non-tool content (incl. attachments); the **main-thread** whole-window total (sidechain volume tallied separately); and the **per-tool resident estimate** (R = first-request `cache_creation_input_tokens × chars_per_token`, minus system-prompt constant S, distributed across the mounted set via heuristic weights), all resident figures labeled estimates with method per research.md D6/D7 (FR-006, FR-009, FR-013) — depends on T007, T009
- [x] T011 Implement `src/throughline/report/model.py`: assemble `ReportData` conforming to contracts/report-data.schema.json — build the mounted set from discovered+config, include the separate `sidechain` object, `sizing.mcp_granularity`, and an **exact** `compaction` retention block (pre/post tokens from `compactMetadata`, labeled exact — FR-024 companion to the per-tool survival estimate) with estimate/availability flags (FR-014, FR-024, D4/D8) — depends on T008, T010
- [x] T012 [P] Implement `src/throughline/report/svg.py`: inline-SVG helpers (bars, grid cells), no external assets (FR-008, research.md D12)
- [x] T013 Implement `src/throughline/report/render.py`: render a single **self-contained** `dashboard.html` shell (inline CSS + SVG), estimate badges, and an explicit "no data" empty state (FR-008, FR-010, SC-004) — depends on T011, T012
- [x] T014 Wire `throughline collect` in `cli.py`: run discovery+copy and ingest any hook data (`calls.log.jsonl`, `backups/precompact/`) if present; print summary per contracts/cli.md (FR-001) — depends on T006
- [x] T015 [P] Write `tests/test_parser.py` (unittest): ordering, tool_use↔tool_result pairing, string/list content sizing, attachment + sidechain tagging, malformed-line tolerance — covers T007
- [x] T016 [P] Write `tests/test_attribution.py` (unittest): mcp/builtin/unattributed bucketing and CLI-wrapped MCP re-attribution — covers T008
- [x] T017 [P] Write `tests/test_mounted.py` (unittest): mounted set assembled from built-in list + MCP config; a declared-but-unused MCP server is present with 0 calls; MCP coverage flagged server-level — covers T009
- [x] T018 [P] Write `tests/test_sizing.py` (unittest): exact per-call/non-tool sizes incl. attachments, main-thread total, sidechain tallied separately, per-tool resident estimate value + labeling — covers T010

**Checkpoint**: `collect` copies real sessions read-only; the pipeline can parse+size, build the mounted set, and emit an (empty-view) dashboard shell.

---

## Phase 3: User Story 1 — Where does my context go (Priority: P1) 🎯 MVP · build step 1

**Goal**: A main-thread whole-window context breakdown by source, per-tool resident (labeled
estimate) separated from per-call, mounted-but-unused tools visible, sidechain volume shown
separately, aggregated across sessions with per-session drilldown.

**Independent Test**: quickstart.md → "US1". Collect, `report`, confirm buckets (built-ins,
MCP server/tool, per-tool resident, non-tool incl. attachments, unattributed) with
amount/frequency/share-of-main-thread-window; resident labeled estimate; ≥1 mounted-but-unused
tool (a built-in or a declared MCP server with 0 calls); buckets sum to the main-thread total;
sidechain reported separately.

- [x] T019 [US1] Implement `src/throughline/analysis/breakdown.py`: aggregate `ContextBucket`s over the **main-thread** window incl. `non_tool` (messages + attachments) and explicit `unattributed`; per-tool resident from `ResidentEstimate` separated from per-call (FR-013); shares of the main-thread window (FR-012); mounted-but-unused from the mounted set — built-ins and declared MCP servers with 0 calls (FR-006, FR-015); completeness so buckets sum to the main-thread total (FR-014, SC-006); sidechain volume kept separate (D4); per-session aggregation (FR-030)
- [x] T020 [US1] Render View 1 (breakdown) in `report/render.py`: per-bucket bars, resident-vs-per-call grouping, **estimate badge + method** on per-tool resident, share labels marked "by size", and a separate sidechain panel
- [x] T021 [US1] Wire `throughline report` in `cli.py` to produce the dashboard with View 1, aggregate by default and `--session <id>` drilldown, `--open` via `file://` per contracts/cli.md (FR-008, FR-030) — depends on T013, T019
- [x] T022 [P] [US1] Write `tests/test_breakdown.py` (unittest): buckets sum to the main-thread total (SC-006), unattributed captures residual, per-tool resident flagged estimate, mounted-but-unused present (built-in AND a declared MCP server with 0 calls), sidechain excluded from the main total — covers T019

**Checkpoint**: MVP — a trustworthy "where does my context go" dashboard from real sessions.

---

## Phase 4: User Story 3 — Tool heatmap (Priority: P3) · build step 2

**Goal**: Every invoked tool on frequency × volume axes, expensive cells obvious;
essentialness shading added later (US4), degrading gracefully until then.

**Independent Test**: quickstart.md → "US3". Every invoked tool placed on both axes;
high-freq/high-volume tools visually distinct.

- [x] T023 [US3] Implement `src/throughline/analysis/heatmap.py`: per-invoked-tool cells with call frequency and total returned volume (FR-016) — depends on T010
- [x] T024 [US3] Render View 2 (heatmap grid) in `report/render.py` + `svg.py`: shade/scale so high-cost cells stand out (FR-017); render without a survival split when unavailable, no fabricated values (FR-018)
- [x] T025 [P] [US3] Write `tests/test_heatmap.py` (unittest): cell freq/volume correctness and graceful no-survival rendering — covers T023

**Checkpoint**: Two trustworthy views (breakdown + heatmap) on the same parsed data.

---

## Phase 5: User Story 4 — Essentialness / survival (Priority: P4) · build steps 3–4

**Goal**: Install the opt-in collection hooks, then estimate per-tool and per-chain survival
across compaction, always labeled an estimate, "unavailable" when uncompacted.

**Independent Test**: quickstart.md → "US4" + "hooks". Install hooks (existing PostToolUse
preserved), use Claude Code, confirm backups appear; survival shows as a labeled estimate; an
uncompacted session shows "unavailable".

### Enabling collection — opt-in hooks (build step 3)

- [x] T026 [US4] Implement `src/throughline/collector/hooks_install.py`: consent-gated **merge** into `~/.claude/settings.json` (back up first, tag entries, atomic write, preserve existing `PostToolUse`), plus `uninstall` (remove only tagged) and `status` per contracts/hooks.md and research.md D10 (FR-007; Principles III/IV/IX)
- [x] T027 [P] [US4] Implement `src/throughline/collector/hook_scripts/post_tool_use.py`: read event JSON on stdin, append one size-only line to `~/.throughline/calls.log.jsonl`, best-effort non-blocking, exit 0 on error (contracts/hooks.md)
- [x] T028 [P] [US4] Implement `src/throughline/collector/hook_scripts/pre_compact.py`: read stdin, fast non-blocking copy of `transcript_path` into `~/.throughline/backups/precompact/`, exit 0 on error. **Optional insurance only** — survival is computed from the transcript (T031); this guards against transcript rotation (contracts/hooks.md, FR-007)
- [x] T029 [US4] Wire `throughline hooks {install,uninstall,status}` in `cli.py` with explicit consent prompt / `--yes` per contracts/cli.md — depends on T026
- [x] T030 [P] [US4] Write `tests/test_hooks_install.py` (unittest): merge preserves a pre-existing `PostToolUse` hook; uninstall removes only Throughline entries; settings.json otherwise byte-identical to backup — covers T026

### Survival estimate (build step 4)

- [x] T031 [US4] Implement `src/throughline/analysis/survival.py`: compute survival **from the transcript** (retroactively; no backup required) — per-tool and per-chain rate = overlap of a tool's distinctive returned values with the post-compaction `isCompactSummary` text; label as estimate; return "unavailable" when no compaction summary exists, per research.md D8 (FR-024, FR-025, FR-026)
- [x] T032 [US4] Integrate survival shading into View 2 and estimate/"unavailable" labels in `report/render.py` (FR-018, FR-025, FR-026) — depends on T024, T031
- [x] T033 [P] [US4] Write `tests/test_survival.py` (unittest): survival rate on a compacted fixture, and the "unavailable" path on an uncompacted fixture — covers T031

**Checkpoint**: Collection is opt-in and reversible; essentialness available where data allows, honestly absent otherwise.

---

## Phase 6: User Story 2 — Sequential patterns (Priority: P2, HEADLINE) · build step 5

**Goal**: Detect recurring data-dependent chains (with fan-out), rank by estimated context
saved, and propose an intent-based tool per top chain. The payoff.

**Independent Test**: quickstart.md → "US2". The fixture chain is detected with recurrence +
total cost, fan-out counts as one logical step, each card shows the never-essential estimate
and a proposal (name/inputs/output/est saved), chains ranked by savings, and coincidental
adjacency yields no chain.

- [x] T034 [US2] Implement `src/throughline/analysis/sequences.py` core: build n-grams (2..max_ngram) of attributed call signatures and keep only sequences with a proven output→input **data dependency**, discarding coincidental adjacency per research.md D9 (FR-019)
- [x] T035 [US2] Add **fan-out** detection in `sequences.py`: one call returning N items followed by ~N near-identical calls, counted as one logical step regardless of N (FR-020) — depends on T034
- [x] T036 [US2] Add cross-session aggregation, `min_recurrence` threshold, scoring `recurrence × total_cost × (1 − survival)` with survival-unavailable fallback, ranking, and overlap/nesting de-duplication (no double-count) in `sequences.py` (FR-022, FR-023) — depends on T035, T031
- [x] T037 [US2] Add intent-tool proposal generation in `sequences.py`: suggested name, inputs, single output, and estimated context saved per session (FR-021) — depends on T036
- [x] T038 [US2] Render View 3 (ranked pattern cards) in `report/render.py`: recurrence, total cost, never-essential estimate (or "unavailable"), collapse proposal, ranked by savings, estimate labels (FR-021, FR-022, FR-025) — depends on T013, T037
- [x] T039 [P] [US2] Write `tests/test_sequences.py` (unittest): data-dependency required (coincidence rejected), fan-out recognized, ranking by savings, de-dup of overlapping chains, proposal fields present — covers T034–T037

**Checkpoint**: All three views complete; the headline miner produces ranked, defensible collapse suggestions.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Verify the constitution gates and harden edge cases.

- [x] T040 [P] Add a local-only guard and an offline test (`tests/test_no_network.py`) proving `collect` and `report` succeed with networking disabled and open no sockets (SC-005, FR-004)
- [x] T041 [P] Add a read-only verification test: hash `~/.claude/projects`, `~/.claude/settings.json`, and the MCP config before/after `collect`+`report`, assert unchanged (SC-007, FR-002)
- [x] T042 [P] Audit generated HTML: every per-tool resident / survival / savings figure carries an estimate badge + method and there are no external/CDN/script-src/font references (SC-004, FR-008)
- [x] T043 [P] Performance check: `report` over a full `~/.claude/projects` copy completes in under 30s (SC-008)
- [x] T044 [P] Edge-case pass: no-data state, session with no tool calls, partial/in-progress transcript, sidechain volume reported separately (not merged into the main total), MCP disconnect/rename → unattributed, built-in-list drift labeled (FR-010, spec Edge Cases)
- [x] T045 [P] Finalize `throughline config --show/--set` and update README/quickstart with the two-command flow and hook opt-in/uninstall

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (P1)** → **Foundational (P2)** → user-story phases → **Polish (P7)**.
- Story phases are ordered by the plan's **build order**, not strict priority number:
  **US1 (P1)** → **US3 (P3)** → **US4 (P4)** → **US2 (P2)**.
  - Rationale: US1's context-cost accounting is the base every view needs; US3 reuses the
    same parsed data cheaply; US4 installs collection + computes the survival signal; the
    **headline US2 miner is last because its scoring uses US4's survival** and it benefits
    from two trustworthy views first.

### Cross-story dependencies

- `parser/mounted.py` (T009) feeds the per-tool resident estimate (T010) and the
  mounted-but-unused breakdown (T019); it is foundational.
- US4 survival (T031) feeds US3 shading (T032) and US2 scoring (T036); US2 falls back to
  `recurrence × total_cost` when survival is unavailable, so US2 is still testable alone.
- Scope-guard requirements FR-027/FR-028/FR-029 (no multi-user/server/cloud, Claude Code
  only, no proxy/behavior change) are enforced by design — nothing to build; T040 and T026
  (observer/opt-in) provide their verification.

### Within a phase

- `[P]` tasks touch different files with no incomplete-task dependency and may run together.
- Tests for a module are written before/alongside that module (Principle X) for the parser
  (T015/T007) and sequence miner (T039/T034–T037).

---

## Parallel Execution Examples

```text
# Setup — independent files:
T003 (config.py)  |  T004 (cli.py skeleton)  |  T005 (fixtures)

# Foundational — discovery, parser, and mounted-set are independent files:
T006 (discover)  |  T007 (parser)  |  T009 (mounted)
# then, after T007: T008 (attribution) ; after T007+T009: T010 (sizing)
T015 (test_parser) | T016 (test_attribution) | T017 (test_mounted) | T018 (test_sizing)

# US4 — hook scripts are independent files:
T027 (post_tool_use.py)  |  T028 (pre_compact.py)  |  T030 (test_hooks_install)

# Polish — all independent verifications:
T040 | T041 | T042 | T043 | T044 | T045
```

---

## Implementation Strategy

### MVP (stop-and-validate after US1)

1. Phase 1 Setup → Phase 2 Foundational → Phase 3 **US1**.
2. Validate against quickstart "US1" and the constitution gates (offline, read-only,
   estimate labels). This alone answers success outcome (a): naming unused mounted tools.

### Incremental delivery (per build order)

US1 (MVP) → add US3 heatmap → add US4 collection+survival → add US2 miner (the payoff,
delivering success outcome (b): top chains to collapse) → Polish. Each phase is an
independently testable increment; stop at any checkpoint.

---

## Notes

- Runtime writes are confined to `~/.throughline/`; the only write into Claude Code's domain
  is the opt-in hook merge (T026), backed up and cleanly reversible. Transcripts, settings,
  and MCP config are read read-only.
- Per-call and non-tool sizes/shares are exact content sizes (chars/bytes), and the
  compaction-retention ratio is exact (pre/post tokens from `compactMetadata`). **Per-tool
  resident cost, survival rate, and projected savings are estimates** and are always labeled
  with their method (per-tool resident uses the disclosed heuristic in research.md D7).
- Survival is computed from the transcript (post-compaction `isCompactSummary` vs each
  tool's returned values), retroactively; the PreCompact backup is optional insurance (D8).
- Mounted-but-unused detection is at **tool** granularity for built-ins and MCP (when
  `preCompactDiscoveredTools` is present), else **server** granularity for MCP (config
  fallback, D7b); the active granularity is labeled in the UI.
- The whole-window total is the **main-thread** window; subagent/sidechain volume is reported
  separately, never folded in (FR-014, D4).
- Commit after each task or logical group; verify tests pass before advancing a phase.
