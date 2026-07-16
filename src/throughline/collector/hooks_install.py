"""Install/uninstall the opt-in Claude Code hooks (contracts/hooks.md, research.md D10).

The ONLY write into Claude Code's domain (Constitution III/IV/IX): consent-gated, backs up
settings.json first, MERGES (never overwrites — a PostToolUse hook may already exist), tags
its own entries (their command path lives under the working dir), and uninstall removes ONLY
those. Hook scripts are copied to ``<working_dir>/hooks/`` so they are self-contained.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

_HOOK_SCRIPTS = Path(__file__).parent / "hook_scripts"
_EVENTS = {"PostToolUse": "post_tool_use.py", "PreCompact": "pre_compact.py"}
_MATCHERS = {"PostToolUse": "*", "PreCompact": "manual|auto"}


def default_settings_path() -> Path:
    return Path.home() / ".claude" / "settings.json"


def _load(settings_path: Path) -> dict:
    if settings_path.exists():
        try:
            return json.loads(settings_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _atomic_write(settings_path: Path, data: dict) -> None:
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = settings_path.with_suffix(settings_path.suffix + ".thl-tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, settings_path)


def _is_ours(group: dict, hooks_dir: Path) -> bool:
    marker = str(hooks_dir)
    for h in group.get("hooks", []) if isinstance(group, dict) else []:
        if isinstance(h, dict) and marker in str(h.get("command", "")):
            return True
    return False


def _copy_scripts(hooks_dir: Path) -> None:
    hooks_dir.mkdir(parents=True, exist_ok=True)
    (hooks_dir / "__init__.py").write_text("", encoding="utf-8")
    for script in _EVENTS.values():
        shutil.copy2(_HOOK_SCRIPTS / script, hooks_dir / script)


def install_hooks(settings_path: Path, hooks_dir: Path, backups_dir: Path) -> dict:
    settings_path = Path(settings_path)
    hooks_dir = Path(hooks_dir)
    backups_dir = Path(backups_dir)

    # 1. back up existing settings (if any)
    backup_path = None
    if settings_path.exists():
        backups_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        backup_path = backups_dir / f"settings.json.{ts}.bak"
        shutil.copy2(settings_path, backup_path)

    # 2. copy standalone hook scripts under the working dir
    _copy_scripts(hooks_dir)

    # 3. merge — preserve everything, add our tagged groups only if not already present
    data = _load(settings_path)
    hooks = data.setdefault("hooks", {})
    added = []
    for event, script in _EVENTS.items():
        groups = hooks.setdefault(event, [])
        if any(_is_ours(g, hooks_dir) for g in groups):
            continue
        command = f"{sys.executable} {hooks_dir / script}"
        groups.append({
            "matcher": _MATCHERS[event],
            "hooks": [{"type": "command", "command": command}],
        })
        added.append(event)

    _atomic_write(settings_path, data)
    return {"installed": True, "added": added, "backup": str(backup_path) if backup_path else None}


def uninstall_hooks(settings_path: Path, hooks_dir: Path) -> dict:
    settings_path = Path(settings_path)
    hooks_dir = Path(hooks_dir)
    data = _load(settings_path)
    hooks = data.get("hooks")
    removed = []
    if isinstance(hooks, dict):
        for event in list(hooks.keys()):
            groups = hooks.get(event)
            if not isinstance(groups, list):
                continue
            kept = [g for g in groups if not _is_ours(g, hooks_dir)]
            if len(kept) != len(groups):
                removed.append(event)
            if kept:
                hooks[event] = kept
            else:
                del hooks[event]
        if not hooks:
            del data["hooks"]
    _atomic_write(settings_path, data)
    return {"installed": False, "removed": removed}


def status_hooks(settings_path: Path, hooks_dir: Path) -> dict:
    settings_path = Path(settings_path)
    hooks_dir = Path(hooks_dir)
    data = _load(settings_path)
    hooks = data.get("hooks", {}) if isinstance(data.get("hooks"), dict) else {}
    ours = {}
    for event, groups in hooks.items():
        if isinstance(groups, list):
            ours[event] = sum(1 for g in groups if _is_ours(g, hooks_dir))
    installed = any(v for v in ours.values())
    return {"installed": installed, "settings_path": str(settings_path), "ours": ours}
