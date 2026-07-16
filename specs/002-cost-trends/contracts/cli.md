# Contract: CLI Additions (feature 002)

Extends 001's command surface. No command makes network calls; no new daemon.

## `throughline report` — new optional filter presets

`report` still generates the single self-contained `dashboard.html` (now with the embedded
cube + interactive filtering). New optional flags **preset the dashboard's initial filter**
(the user can still change it live in the browser):

| Flag | Effect |
|------|--------|
| `--project <substr>` | Initial project filter (matches a `dims.projects` entry). |
| `--from <YYYY-MM-DD>` | Initial time-range start. |
| `--to <YYYY-MM-DD>` | Initial time-range end. |

These write `initial_filter` into the embedded blob; they do **not** reduce what data is
embedded (all sessions remain available so the user can widen the filter in-browser). Exit
codes unchanged from 001 (`0` ok, `3` no collected data).

## `throughline note <add|list|remove>` — interventions (US4)

Manage dated intervention notes stored at `~/.throughline/interventions.json`.

| Subcommand | Contract |
|------------|----------|
| `note add --date <YYYY-MM-DD> --label "<text>"` | Append `{date, label}`. Validates date format; writes only within the working dir. |
| `note list` | Print recorded interventions. |
| `note remove --date <YYYY-MM-DD> [--label "<text>"]` | Remove matching note(s). |

Notes are embedded into the next `report` and drawn as marker lines on trends spanning their
date. Exit `0` on success; `1` on bad input.

## Unchanged

`collect`, `hooks {install,uninstall,status}`, `config` behave as in 001. `report --open`
and per-session `--session` still work. The two everyday commands remain `collect` + `report`
(SC-003 / Principle VI); `note` is an occasional annotation aid.
