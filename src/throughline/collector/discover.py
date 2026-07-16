"""Discover Claude Code session transcripts and copy them into the working directory.

Claude Code files are READ-ONLY inputs (Constitution III): the source is never opened for
write; we copy each transcript into ``<working_dir>/transcripts/`` and parse the copy.
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class SessionRef:
    session_id: str
    project: str
    source_path: Path
    mtime: float
    size_bytes: int


def discover_sessions(
    transcript_dir: str | Path,
    since: str | None = None,
    project: str | None = None,
) -> list[SessionRef]:
    """List `.jsonl` sessions under transcript_dir/<project>/<uuid>.jsonl (read-only)."""
    root = Path(transcript_dir).expanduser()
    refs: list[SessionRef] = []
    if not root.exists():
        return refs
    since_ts = _parse_since(since)
    for path in sorted(root.glob("*/*.jsonl")):
        try:
            st = path.stat()
        except OSError:
            continue
        proj = path.parent.name.replace("-", "/")
        if project and project not in proj:
            continue
        if since_ts is not None and st.st_mtime < since_ts:
            continue
        refs.append(
            SessionRef(
                session_id=path.stem,
                project=proj,
                source_path=path,
                mtime=st.st_mtime,
                size_bytes=st.st_size,
            )
        )
    return refs


def copy_sessions(refs: list[SessionRef], dest_dir: str | Path) -> list[Path]:
    """Copy each transcript into dest_dir (read-only on source). Returns copied paths."""
    dest = Path(dest_dir).expanduser()
    dest.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    for ref in refs:
        # preserve the project subdir so parse_transcript recovers the repo (feature 002)
        sub = dest / ref.source_path.parent.name
        sub.mkdir(parents=True, exist_ok=True)
        target = sub / f"{ref.session_id}.jsonl"
        # copy2 preserves metadata but never modifies the source
        shutil.copy2(ref.source_path, target)
        copied.append(target)
    return copied


def list_copied(dest_dir: str | Path) -> list[Path]:
    dest = Path(dest_dir).expanduser()
    if not dest.exists():
        return []
    # per-project subdirs (preferred); fall back to a flat layout for older collections
    return sorted(dest.glob("*/*.jsonl")) or sorted(dest.glob("*.jsonl"))


def _parse_since(since: str | None) -> float | None:
    if not since:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            dt = datetime.strptime(since, fmt).replace(tzinfo=timezone.utc)
            return dt.timestamp()
        except ValueError:
            continue
    return None
