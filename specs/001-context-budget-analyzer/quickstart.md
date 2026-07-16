# Quickstart & Validation: Throughline — Context Budget Analyzer

A run/validation guide. Each scenario is verifiable end-to-end and maps to a user story or
constitution gate. Implementation code lives in the source tree; test bodies live in
`tests/`. See [contracts/](./contracts/) and [data-model.md](./data-model.md) for details.

## Prerequisites

- Python 3.11+ (`python3 --version`).
- No installation of third-party packages (there are none).
- Some real Claude Code sessions under `~/.claude/projects/` (or use the fixtures in
  `tests/fixtures/` for a deterministic run).

## Install (local, no network)

```bash
# from the repo root
python -m throughline --help          # or: pip install -e .  (metadata only, no deps)
```

## The two-command happy path (SC-003)

```bash
python -m throughline collect         # copies transcripts read-only into ~/.throughline/
python -m throughline report --open   # writes ~/.throughline/out/dashboard.html and opens it
```

Expected: `collect` prints sessions found/copied; `report` prints the HTML path and opens it
via `file://` with no server.

---

## Story validations

### US1 — Where does my context go (P1)

1. `python -m throughline collect && python -m throughline report`.
2. Open the dashboard; confirm the **context breakdown** shows buckets: each built-in tool
   named separately, MCP tools grouped by server→tool, **per-tool resident** entries, a
   **non-tool content** bucket (messages + attachments/files read), and an **unattributed**
   bucket.
3. Confirm each bucket shows amount (size), frequency, and **share of the whole main-thread
   window**; per-tool resident is shown distinctly from per-call and carries an **estimate**
   badge with its method (FR-006, FR-013, FR-025).
4. Confirm at least one **mounted-but-never-called** tool appears with count 0 — e.g. a
   built-in you didn't use, or an MCP **server** declared in local config with zero calls
   (FR-006, FR-015).
5. Confirm the buckets **sum to the total main-thread window size** (SC-006) — a displayed
   total with no silent remainder; leftover shows under "unattributed".
6. Confirm **subagent/sidechain** volume is reported **separately**, not folded into the
   main-thread total (FR-014).
7. Confirm a **per-session drilldown** is available (FR-030): `report --session <id>`.

### US3 — Tool heatmap (P3)

1. On the dashboard, confirm every invoked tool appears on **frequency × volume** axes.
2. Confirm high-frequency + high-volume tools are visually distinct (shading/size).
3. If survival data exists, confirm the **essentialness shading** shows and is labeled an
   estimate; if not, the cell still renders on both axes with no fabricated split (FR-018).

### Collection via opt-in hooks (enables US4)

1. `python -m throughline hooks status` → shows not installed.
2. `python -m throughline hooks install` → prompts for consent; on `yes`:
   - `~/.claude/settings.json` is **backed up** to `~/.throughline/backups/`.
   - Throughline's `PostToolUse` + `PreCompact` entries are **merged in**, and the
     **pre-existing `PostToolUse` hook is still present** (diff the backup — only additions).
3. Use Claude Code normally for a while.
4. Confirm `~/.throughline/calls.log.jsonl` grows and, after any compaction,
   `~/.throughline/backups/precompact/` contains a snapshot.
5. `python -m throughline hooks uninstall` → only Throughline entries removed; settings.json
   otherwise identical to pre-install (diff to confirm) (Principles III/IX).

### US4 — Essentialness / survival (P4)

1. With at least one session that hit a `compact_boundary` **and** has a PreCompact backup:
   `python -m throughline report`.
2. Confirm per-tool **survival rate** is shown, **labeled an estimate** with its method
   (FR-025).
3. On a session that never compacted, confirm survival shows **"unavailable"** — not a
   number (FR-026).

### US2 — Sequential patterns (P2, headline)

1. Ensure several sessions contain a repeated, data-dependent sequence (fixtures include a
   `get sprint → get team → get stories → get status ×N` chain with a fan-out).
2. `python -m throughline report`; open the **Sequential Patterns** view.
3. Confirm the chain is detected with its **recurrence count** and **total context cost**.
4. Confirm the **fan-out** step is recognized and counts as one logical step even as N
   varies (FR-020).
5. Confirm each card shows the **intermediate-never-essential** portion (labeled estimate,
   or "unavailable"), and a **proposed intent tool**: name, inputs, single output, and
   **estimated context saved** (FR-021).
6. Confirm chains are **ranked by estimated savings**, top 2–3 obvious (FR-022, SC-002).
7. Confirm coincidental adjacency (no data dependency) is **not** reported as a chain
   (FR-019) — a fixture with co-occurring-but-unrelated calls yields no chain.

---

## Constitution gate checks

| Gate | How to verify |
|------|---------------|
| Local-Only (SC-005) | Run `collect` and `report` with networking disabled (e.g. `sudo ifconfig` down, or a sandbox with no net). Both succeed. Optionally confirm no socket use. |
| Read-Only toward Claude Code (SC-007) | Hash `~/.claude/projects` (and settings.json) before/after `collect` and `report`; unchanged. Only `hooks install` changes settings.json, and only additively. |
| Writes confined (FR-003) | After all commands, confirm no files created outside `~/.throughline/` (and, for install, the single settings.json merge). |
| Estimates labeled (SC-004) | Grep the generated HTML: every resident/survival/savings figure carries an "estimate" badge + method; size/share figures do not. |
| Self-contained HTML (FR-008) | Open `dashboard.html` from `file://` with no server and no network; confirm no `<script src>`/CDN/external-font references. |
| Simple to run (SC-003) | The whole flow is `collect` then `report`; no daemon/process left running. |

## Fixture-based deterministic run (CI-friendly, no real data)

```bash
python -m unittest discover -s tests          # parser, attribution, sizing, survival, sequences, hooks-install
python -m throughline report --transcript-dir tests/fixtures --out /tmp/thl-demo.html
```

Expected: tests pass; a dashboard renders from fixtures with a known chain ranked first and
a known mounted-but-unused tool in the breakdown.

## Performance check (SC-008)

`time python -m throughline report` on a full `~/.claude/projects` copy completes in under
30 seconds.
