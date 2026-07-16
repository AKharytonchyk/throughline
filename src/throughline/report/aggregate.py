"""Build the pre-aggregated EmbeddedData blob the client (app.js) consumes (feature 002).

The Python analysis runs ONCE here; the browser only sums/groups this output. Conforms to
contracts/embedded-data.schema.json. The full cube reproduces feature 001's totals (golden
check, research.md D8) — that is what makes the client aggregation trustworthy.
"""
from __future__ import annotations

import hashlib

from throughline.analysis import sizing
from throughline.analysis import survival as survival_mod
from throughline.analysis import sequences as seq
from throughline.analysis import tokens as tokens_mod
from throughline.analysis import cost as cost_mod
from throughline.analysis.timeline import day_of
from throughline.config import Config
from throughline.parser.mounted import MountedTool

MODES = ["plan", "auto", "acceptEdits", "default", "unknown"]


def _tool_meta(key: str) -> dict:
    if key.startswith("mcp:"):
        rest = key[4:]
        server, tool = (rest.split("/", 1) + [None])[:2] if "/" in rest else (rest, None)
        return {"key": key, "kind": "mcp_tool", "server": server, "tool": tool}
    if key.startswith("builtin:"):
        return {"key": key, "kind": "builtin", "server": None, "tool": key.split(":", 1)[1]}
    return {"key": key, "kind": "unattributed", "server": None, "tool": None}


def _idx(lookup: dict, seq_list: list, value):
    if value not in lookup:
        lookup[value] = len(seq_list)
        seq_list.append(value)
    return lookup[value]


def build_embedded_data(sessions: list, mounted: list[MountedTool], cfg: Config,
                        interventions: list | None = None,
                        initial_filter: dict | None = None,
                        price_list: dict | None = None) -> dict:
    # ---- pass 1: collect dims (days must be sorted for the trend x-axis) ----
    day_set, project_set, tool_key_set, session_ids = set(), set(), set(), []
    session_day = {}  # session_id -> representative day (earliest call day)
    for s in sessions:
        project_set.add(s.project)
        session_ids.append(s.session_id)
        earliest = None
        for c in s.main_thread_calls():
            d = day_of(c.timestamp) or "undated"
            day_set.add(d)
            tool_key_set.add(c.key)
            if earliest is None or d < earliest:
                earliest = d
        session_day[s.session_id] = earliest or "undated"
        if session_day[s.session_id] == "undated":
            day_set.add("undated")
        # feature 003 (isolated): per-turn usage days also index into shared dims.days
        # (for by_day buckets + the shared date-range control) without perturbing the
        # occupancy representative day above.
        for u in getattr(s, "turn_usages", []):
            day_set.add(day_of(u.ts) or "undated")

    days = sorted(day_set)
    day_i = {d: i for i, d in enumerate(days)}
    projects = sorted(project_set)
    proj_i = {p: i for i, p in enumerate(projects)}
    tool_keys = sorted(tool_key_set)
    tool_i = {k: i for i, k in enumerate(tool_keys)}
    mode_i = {m: i for i, m in enumerate(MODES)}
    sess_i = {sid: i for i, sid in enumerate(session_ids)}

    # ---- pass 2: cube + session facts ----
    cube_map: dict[tuple, list] = {}  # (p,d,t,m,sess) -> [n, s]
    session_facts = []
    for s in sessions:
        p = proj_i[s.project]
        sd = day_i[session_day[s.session_id]]
        si = sess_i[s.session_id]
        for c in s.main_thread_calls():
            d = day_i[day_of(c.timestamp) or "undated"]
            key = (p, d, tool_i[c.key], mode_i.get(c.mode, mode_i["unknown"]), si)
            cell = cube_map.setdefault(key, [0, 0])
            cell[0] += 1
            cell[1] += c.input_size + c.output_size
        res = sizing.resident_estimate(s, mounted, cfg)
        session_facts.append({
            "p": p, "d": sd, "sess": si,
            "resident_est": res.total_overhead_size,
            "non_tool": s.non_tool_size,
            "sidechain_size": sizing.sidechain_total(s),
            "sidechain_calls": sum(1 for c in s.tool_calls if c.is_sidechain),
        })

    cube = [{"p": k[0], "d": k[1], "t": k[2], "m": k[3], "sess": k[4], "n": v[0], "s": v[1]}
            for k, v in cube_map.items()]

    # ---- chains: occurrences (per session) + shapes ----
    shapes: dict[str, dict] = {}
    occurrences = []
    for s in sessions:
        p = proj_i[s.project]
        sd = day_i[session_day[s.session_id]]
        si = sess_i[s.session_id]
        steps = seq._collapse_fanout(s.main_thread_calls())
        for chain in seq._extract_chains(steps):
            sig = tuple((steps[k].key, steps[k].fanout) for k in chain)
            chain_id = hashlib.sha1(repr(sig).encode()).hexdigest()[:12]
            total_cost = sum(steps[k].cost for k in chain)
            intermediate = max(total_cost - steps[chain[-1]].last_output, 0)
            occurrences.append({"chain_id": chain_id, "p": p, "d": sd, "sess": si,
                                "total_cost": total_cost, "intermediate": intermediate})
            if chain_id not in shapes:
                shorts = [seq._short(steps[k].key) for k in chain]
                first_inputs = sorted(steps[chain[0]].input_values)[:3]
                shapes[chain_id] = {
                    "chain_id": chain_id,
                    "steps": [{"signature": steps[k].key, "fanout": steps[k].fanout} for k in chain],
                    "proposal": {
                        "suggested_name": ("_".join(shorts)[:64] or "intent_tool"),
                        "inputs": first_inputs or [shorts[0] + " inputs"],
                        "output": shorts[-1] + " result",
                    },
                }

    # ---- survival (global per tool) ----
    surv_map, _ = survival_mod.compute_survival(sessions)
    by_tool = {}
    for (scope, key), v in surv_map.items():
        if scope == "tool" and key in tool_i and v.get("available"):
            by_tool[str(tool_i[key])] = v.get("rate")
    survival = {"available": bool(by_tool), "by_tool": by_tool}

    # ---- compaction (exact retention, carried from 001) ----
    events = [e for s in sessions for e in s.compaction_events]
    pre = sum(e["pre_tokens"] for e in events)
    post = sum(e["post_tokens"] for e in events)
    compaction = {"events": len(events), "pre_tokens": pre, "post_tokens": post,
                  "retention_pct": (post / pre * 100) if pre else None, "exact": True}

    mounted_keys = sorted({
        (m.name if m.name.startswith("mcp:") else f"builtin:{m.name}") for m in mounted
    })

    # ---- token flow (feature 003): a SEPARATE section; never merged with cube/session_facts ----
    token_sessions = []
    models_seen: set[str] = set()
    no_usage_count = 0
    for s in sessions:
        flow = tokens_mod.session_flow(s)
        if flow["no_usage"]:
            no_usage_count += 1
        models_seen.update(flow["by_model"].keys())
        # representative day for session-level project+date filtering (earliest usage day;
        # falls back to the occupancy representative day when the session has no usage turns)
        udays = [day_of(u.ts) or "undated" for u in getattr(s, "turn_usages", [])]
        rep_day = min(udays) if udays else session_day[s.session_id]
        token_sessions.append({
            "session": flow["session"],
            "p": proj_i[s.project],
            "d": day_i[rep_day],
            "turns": flow["turns"],
            "no_usage": flow["no_usage"],
            "totals": flow["totals"],
            "by_model": flow["by_model"],
            "growth": tokens_mod.growth_series(s),
        })
    token_flow = {
        "unit": "tokens",
        "sessions": token_sessions,
        "by_day": tokens_mod.by_day_buckets(sessions, proj_i, day_i),
        "models": sorted(models_seen),
        "coverage": {"sessions_total": len(sessions), "sessions_no_usage": no_usage_count},
    }
    cost = cost_mod.estimate(tokens_mod.sum_by_model(token_sessions), price_list)
    if cost:  # attach only when a non-empty price list was loaded (US4 / FR-010)
        token_flow["cost"] = cost

    from datetime import datetime, timezone
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "unit": cfg.size_unit,
        "dims": {
            "projects": projects,
            "days": days,
            "tools": [_tool_meta(k) for k in tool_keys],
            "modes": MODES,
        },
        "mounted_keys": mounted_keys,
        "cube": cube,
        "session_facts": session_facts,
        "token_flow": token_flow,
        "chain_shapes": list(shapes.values()),
        "chain_occurrences": occurrences,
        "survival": survival,
        "compaction": compaction,
        "interventions": interventions or [],
        "min_recurrence": cfg.min_recurrence,
        "initial_filter": initial_filter,
    }
