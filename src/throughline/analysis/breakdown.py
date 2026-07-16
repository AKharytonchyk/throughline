"""View 1 — context breakdown across the MAIN-THREAD window (FR-011..015, FR-030).

Every unit of main-thread ingested content lands in exactly one bucket — per built-in tool,
per MCP server/tool, per-tool resident (estimate), non-tool content (messages + attachments),
or explicit unattributed — and the buckets sum to the main-thread total (SC-006). Resident
buckets cover the whole mounted set, so a mounted-but-never-called tool appears with 0 calls.
Subagent/sidechain volume is reported separately (D4).
"""
from __future__ import annotations

from throughline.analysis import sizing
from throughline.config import Config
from throughline.parser.mounted import MountedTool


def _kind_for(key: str) -> str:
    if key.startswith("mcp:"):
        return "mcp_tool"
    if key.startswith("builtin:"):
        return "builtin"
    return "unattributed"


def aggregate_breakdown(sessions: list, mounted: list[MountedTool], cfg: Config) -> dict:
    per_call_size: dict[str, int] = {}
    call_count: dict[str, int] = {}
    resident_size: dict[str, int] = {}
    non_tool_total = 0
    system_prompt_total = 0
    grand_total = 0
    sidechain_size = 0
    sidechain_calls = 0

    for sess in sessions:
        res = sizing.resident_estimate(sess, mounted, cfg)
        grand_total += sizing.main_thread_total(sess, res)
        non_tool_total += sess.non_tool_size
        system_prompt_total += res.system_prompt_size
        for key, sz in res.per_tool.items():
            resident_size[key] = resident_size.get(key, 0) + sz
        for c in sess.main_thread_calls():
            per_call_size[c.key] = per_call_size.get(c.key, 0) + c.input_size + c.output_size
            call_count[c.key] = call_count.get(c.key, 0) + 1
        sidechain_size += sizing.sidechain_total(sess)
        sidechain_calls += sum(1 for c in sess.tool_calls if c.is_sidechain)

    buckets: list[dict] = []

    # Resident buckets (estimates) — cover the whole mounted set (incl. never-called).
    if system_prompt_total:
        buckets.append(_bucket(
            "resident:system_prompt", "resident", "resident", system_prompt_total,
            0, grand_total, is_estimate=True, method=sizing.RESIDENT_METHOD,
        ))
    for key in sorted(resident_size):
        server, tool = _split_key(key)
        buckets.append(_bucket(
            key, "resident", "resident", resident_size[key], call_count.get(key, 0),
            grand_total, server=server, tool=tool, is_estimate=True,
            method=sizing.RESIDENT_METHOD,
        ))

    # Per-call buckets (exact) — built-in + MCP tool + unattributed.
    for key in sorted(per_call_size):
        server, tool = _split_key(key)
        buckets.append(_bucket(
            key, _kind_for(key), "per_call", per_call_size[key], call_count.get(key, 0),
            grand_total, server=server, tool=tool, is_estimate=False,
        ))

    # Always-present non-tool and unattributed buckets (explicit, even if zero).
    buckets.append(_bucket("non_tool", "non_tool", "per_call", non_tool_total, 0, grand_total))
    if "unattributed" not in per_call_size:
        buckets.append(_bucket("unattributed", "unattributed", "per_call", 0, 0, grand_total))

    warnings: list[str] = []
    if not sessions:
        warnings.append("No sessions collected yet — run `throughline collect` first.")

    return {
        "breakdown": buckets,
        "sidechain": {"size": sidechain_size, "calls": sidechain_calls},
        "main_thread_total": grand_total,
        "warnings": warnings,
    }


def _split_key(key: str):
    if key.startswith("mcp:"):
        rest = key[4:]
        if "/" in rest:
            server, tool = rest.split("/", 1)
            return server, tool
        return rest, None
    return None, None


def _bucket(key, kind, cost_kind, total_size, call_count, grand_total,
            server=None, tool=None, is_estimate=False, method=None):
    return {
        "key": key,
        "kind": kind,
        "cost_kind": cost_kind,
        "server": server,
        "tool": tool,
        "total_size": total_size,
        "call_count": call_count,
        "share": (total_size / grand_total) if grand_total else 0.0,
        "is_estimate": is_estimate,
        "estimate_method": method,
    }
