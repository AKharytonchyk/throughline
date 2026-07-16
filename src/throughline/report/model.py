"""Assemble the ReportData object consumed by the renderer.

Conforms to contracts/report-data.schema.json (plus a `compaction` block for the exact
retention figure). Decouples analysis from rendering so both are independently testable.
Every estimated value carries a flag so the renderer labels it; the compaction retention is
marked exact.
"""
from __future__ import annotations

from datetime import datetime, timezone

from throughline.analysis import breakdown as breakdown_mod
from throughline.analysis import heatmap as heatmap_mod
from throughline.analysis import sequences as sequences_mod
from throughline.analysis import survival as survival_mod
from throughline.analysis import sizing
from throughline.config import Config
from throughline.parser.mounted import build_mounted_set, BUILTIN_TOOLS_VERSION


def build_report(sessions: list, cfg: Config, session_id: str | None = None) -> dict:
    if session_id:
        sessions = [s for s in sessions if s.session_id == session_id]

    discovered: set = set()
    for s in sessions:
        discovered |= s.discovered_tools
    mounted = build_mounted_set(cfg.mcp_config_paths, discovered_tools=discovered)

    survival, surv_warnings = survival_mod.compute_survival(sessions)
    bd = breakdown_mod.aggregate_breakdown(sessions, mounted, cfg)
    heat = heatmap_mod.build_heatmap(sessions, survival)
    chains = sequences_mod.mine_sequences(sessions, cfg, survival)
    compaction = _compaction(sessions)

    mcp_granularity = "tool" if discovered else "server"
    warnings = list(bd["warnings"]) + list(surv_warnings)
    if not sessions:
        warnings.insert(0, "No data to show. Run `throughline collect`, then `report`.")
    elif mcp_granularity == "server":
        warnings.append(
            "MCP mounted-but-unused coverage is at server granularity — collect a session "
            "that underwent compaction for exact tool-level coverage."
        )
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": {
            "sessions": len(sessions), "from": None, "to": None,
            "aggregate": not session_id, "session_id": session_id,
        },
        "sizing": {
            "unit": cfg.size_unit, "chars_per_token": cfg.chars_per_token,
            "method_notes": (
                f"Per-call and non-tool sizes are exact ({cfg.size_unit}). Resident cost is a "
                f"per-tool estimate: {sizing.RESIDENT_METHOD} Mounted set from "
                f"{'compaction-discovered tools (MCP tool-level)' if discovered else 'local config (MCP server-level)'}. "
                f"Built-in list: {BUILTIN_TOOLS_VERSION}."
            ),
            "mcp_granularity": mcp_granularity,
        },
        "breakdown": bd["breakdown"],
        "sidechain": bd["sidechain"],
        "compaction": compaction,
        "heatmap": heat,
        "chains": chains,
        "warnings": warnings,
        "_main_thread_total": bd["main_thread_total"],
    }


def _compaction(sessions: list) -> dict:
    events = [e for s in sessions for e in s.compaction_events]
    pre = sum(e["pre_tokens"] for e in events)
    post = sum(e["post_tokens"] for e in events)
    return {
        "events": len(events),
        "pre_tokens": pre,
        "post_tokens": post,
        "retention_pct": (post / pre * 100) if pre else None,  # EXACT (from Claude Code)
        "exact": True,
    }
