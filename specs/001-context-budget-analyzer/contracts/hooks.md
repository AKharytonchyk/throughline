# Contract: Hook Scripts I/O + settings.json Merge

Two standalone hook scripts live under `src/throughline/collector/hook_scripts/` and write
only within `~/.throughline/`. They are passive: log/copy only, never altering Claude
Code's behavior (Principle IV). Both read a single JSON object from **stdin**.

## PostToolUse hook — `post_tool_use.py`

**Stdin (JSON)** — fields the script relies on (extra fields ignored):

| Field | Type | Use |
|-------|------|-----|
| `session_id` | str | Attribute the call to a session. |
| `tool_name` | str | Bucketing later. |
| `tool_input` | any | Recorded as size (and optionally value) — see privacy note. |
| `tool_output` / `tool_response` | any | Measured for `tool_output` size. |

**Action**: append exactly one line to `~/.throughline/calls.log.jsonl`:

```json
{"ts":"<ISO8601>","session_id":"...","tool_name":"...","input_size":<int>,"output_size":<int>}
```

**Guarantees**: append-only; O(1) work; never blocks or delays the tool result; exits `0`
even on internal error (a logging failure must never disrupt Claude Code — best-effort,
swallow-and-exit). Writes nothing outside `~/.throughline/`.

**Privacy note**: default records **sizes only** for `tool_input`/`tool_output`; full
content stays in the transcripts the parser already reads. This keeps the log small and
avoids duplicating sensitive content (Principle II).

## PreCompact hook — `pre_compact.py`

**Stdin (JSON)**:

| Field | Type | Use |
|-------|------|-----|
| `session_id` | str | Names the backup. |
| `transcript_path` | path | Source to snapshot (insurance; the on-disk transcript already retains detail). |
| `cwd` | str | Recorded for context. |

**Action**: copy `transcript_path` → `~/.throughline/backups/precompact/<session_id>-<ts>.jsonl`.

**Guarantees**: trigger + copy only; **fast and non-blocking** — dispatch the copy without
delaying compaction (detach/return immediately) and return promptly; read-only on the
source; exits `0` on error (best-effort). Writes only under `~/.throughline/`.

**Note (optional insurance)**: the essentialness/survival signal is computed from the
transcript itself — the pre-compaction detail and the `isCompactSummary` summary both
persist on disk (research.md D8). This backup is therefore *not* required for survival; it
only guards against transcript rotation/truncation. No "post-compact" hook is needed.

## settings.json merge contract (`hooks install`)

1. **Consent required** before any write.
2. **Back up** `~/.claude/settings.json` → `~/.throughline/backups/settings.json.<ts>.bak`.
3. **Merge, do not overwrite**: load JSON, ensure `hooks` object, append Throughline's
   entries under the `PostToolUse` and `PreCompact` event arrays. **Existing hooks (a
   `PostToolUse` hook already exists on this machine) MUST be preserved.**
4. **Tag** each inserted entry with a stable identifier (e.g. a `command` path under
   `~/.throughline/` and/or a recognizable marker) so uninstall can find exactly its own
   entries.
5. Write **atomically** (temp file + replace).

**`hooks uninstall`**: reverse of step 3 — remove only entries matching the Throughline
tag; if the resulting event array is empty, remove it; leave everything else untouched. The
pre-write backup remains available for manual restore.

**Non-negotiables**: never modify keys outside `hooks`; never remove or rewrite a
non-Throughline hook; the operation is fully reversible (Principles III & IX).
