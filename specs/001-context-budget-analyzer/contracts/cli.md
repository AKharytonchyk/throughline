# Contract: CLI Command Surface

The tool's primary external interface. Invoked as `throughline <command>` (console script)
or `python -m throughline <command>`. Text in → stdout; errors → stderr; non-zero exit on
failure. No command performs any network access.

## `throughline collect`

Gather usage data read-only into the working directory.

| Aspect | Contract |
|--------|----------|
| Options | `--transcript-dir PATH` (override config), `--since DATE`, `--project NAME`, `--all` (default), `--dry-run` (list what would be copied). |
| Behavior | Discover sessions under `transcript_dir`; **copy** each selected transcript into `working_dir/transcripts/` (never open source for write). Merge in any `calls.log.jsonl` and `backups/precompact/` produced by installed hooks. |
| Output | Summary to stdout: sessions found/copied, date range, whether hook data is present. |
| Exit | `0` success; `2` transcript_dir missing/unreadable; `1` unexpected error. |
| Guarantees | Writes only under `working_dir` (FR-003); makes zero network calls (SC-005); leaves Claude Code files byte-identical (SC-007). |

## `throughline report`

Produce the dashboard from already-collected data. Fully offline.

| Aspect | Contract |
|--------|----------|
| Options | `--out PATH` (override `output_path`), `--session ID` (per-session drilldown; default aggregate across all — FR-030), `--open` (open in default browser via `file://`). |
| Behavior | Parse copied transcripts → analyze → render single self-contained `dashboard.html`. |
| Output | Path to the generated HTML on stdout. |
| Exit | `0` success; `3` no collected data (prints how to `collect`); `1` unexpected error. |
| Guarantees | Output is one HTML file, no external/CDN assets, opens without a server (FR-008); every estimate labeled (SC-004); "no data"/"survival unavailable" stated explicitly (FR-010). |

## `throughline hooks <install|uninstall|status>`

Manage the opt-in Claude Code hooks. See `hooks.md` for the I/O and merge contract.

| Subcommand | Contract |
|------------|----------|
| `install` | Requires explicit consent (interactive confirm, or `--yes`). Backs up `~/.claude/settings.json`, then **merges** Throughline's `PostToolUse` + `PreCompact` entries, preserving existing hooks. Records opt-in state in config. |
| `uninstall` | Removes **only** Throughline-tagged hook entries; restores prior shape; updates config. |
| `status` | Prints whether hooks are installed, the settings.json path, backup location, and captured-data counts. Read-only. |
| Exit | `0` success; `4` consent declined / not installed; `1` unexpected error. |
| Guarantees | The only write into Claude Code's domain; consent-gated; reversible; never overwrites unrelated settings (Principles III/IV/IX). |

## `throughline config [--show|--set KEY=VALUE]`

Show or edit `working_dir/config.json`. `--set` validates keys against the Config model.
No network keys accepted. `--show` (default) prints current effective config.

## Global behavior

- `--help`/`-h` on any command prints usage.
- All commands are idempotent-safe to re-run.
- No command starts a long-running process or daemon (SC-003).
