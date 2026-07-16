#!/usr/bin/env python3
"""Throughline PreCompact hook (standalone; stdlib only).

Reads the event JSON on stdin and backs up the current transcript BEFORE compaction
discards the pre-compaction detail. Trigger + copy only: fast, non-blocking, read-only on
the source, and swallows all errors. Writes only under ``<working_dir>/backups/precompact/``.
"""
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:
        return 0
    try:
        transcript = event.get("transcript_path")
        session_id = event.get("session_id") or "unknown"
        if not transcript:
            return 0
        src = Path(transcript).expanduser()
        if not src.exists():
            return 0
        working = Path(__file__).resolve().parent.parent  # <working_dir>/hooks/ -> <working_dir>
        dest_dir = working / "backups" / "precompact"
        dest_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        # read-only on source; copy is small and returns promptly (non-blocking in practice)
        shutil.copy2(src, dest_dir / f"{session_id}-{ts}.jsonl")
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
