#!/usr/bin/env python3
"""Throughline PostToolUse hook (standalone; stdlib only).

Reads the event JSON on stdin and appends ONE size-only line to
``<working_dir>/calls.log.jsonl``. Logs only — never blocks, never alters Claude Code
behavior, and swallows all errors (a logging failure must never disrupt a session).

Records SIZES only (not full input/output content) to keep the log small and avoid
duplicating sensitive content — the full content already lives in the transcripts.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def _size(v):
    if v is None:
        return 0
    s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False, default=str)
    return len(s)


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:
        return 0
    try:
        working = Path(__file__).resolve().parent.parent  # <working_dir>/hooks/ -> <working_dir>
        log = working / "calls.log.jsonl"
        log.parent.mkdir(parents=True, exist_ok=True)
        rec = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "session_id": event.get("session_id"),
            "tool_name": event.get("tool_name"),
            "input_size": _size(event.get("tool_input")),
            "output_size": _size(event.get("tool_output") or event.get("tool_response")),
        }
        with log.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
