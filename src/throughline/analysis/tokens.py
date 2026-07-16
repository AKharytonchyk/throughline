"""Token-flow analysis (feature 003) — the FLOW model, kept separate from the occupancy
(chars) model of features 001/002.

Everything here is pure and derived from the per-turn ``usage`` blocks the parser now
captures (``ParsedSession.turn_usages``). Token counts are **read, not estimated** — that is
what makes the "exact" label (FR-004) truthful. The four types are:

    input        <- input_tokens
    output       <- output_tokens
    cache_write  <- cache_creation_input_tokens
    cache_read   <- cache_read_input_tokens

The Python side builds a compact ``token_flow`` blob section (per-session totals + per-model
split + a downsampled growth series, plus per-(project,day) buckets); the browser only sums
and renders it. Reconciliation (SC-002) holds by construction and is asserted by a golden test.
"""
from __future__ import annotations

from throughline.analysis.timeline import day_of

FLOW_KEYS = ("input", "output", "cache_write", "cache_read")

GROWTH_CAP = 120  # max points embedded per session's growth curve (research D4)


def empty_totals() -> dict:
    return {"input": 0, "output": 0, "cache_write": 0, "cache_read": 0}


def add_usage(totals: dict, u) -> None:
    """Accumulate one TurnUsage into a FlowTotals dict (in place)."""
    totals["input"] += u.input
    totals["output"] += u.output
    totals["cache_write"] += u.cache_write
    totals["cache_read"] += u.cache_read


def total_of(t: dict) -> int:
    """Raw, unweighted sum of the four token types (research D1)."""
    return t["input"] + t["output"] + t["cache_write"] + t["cache_read"]


def cache_read_share(t: dict) -> float:
    """cache_read / total (FR-005); 0.0 when total is 0 (never NaN)."""
    tot = total_of(t)
    return (t["cache_read"] / tot) if tot else 0.0


def session_flow(session) -> dict:
    """Per-session flow record (analysis → blob contract).

    ``{session, project, turns, no_usage, totals, by_model}`` where ``Σ by_model == totals``.
    ``no_usage`` is True iff the session had assistant turns but **none** carried a usage
    block (flagged, not dropped — research D2). Growth/by_day are added by the callers below.
    """
    totals = empty_totals()
    by_model: dict[str, dict] = {}
    for u in session.turn_usages:
        add_usage(totals, u)
        add_usage(by_model.setdefault(u.model, empty_totals()), u)
    return {
        "session": session.session_id,
        "project": session.project,
        "turns": len(session.turn_usages),
        "no_usage": not session.turn_usages and getattr(session, "no_usage_turns", 0) > 0,
        "totals": totals,
        "by_model": by_model,
    }


def _sample_indices(n: int, cap: int) -> list[int]:
    """<= cap evenly-spaced turn indices over [0, n-1], always including first and last."""
    if n <= cap:
        return list(range(n))
    idxs = {0, n - 1}
    for k in range(cap):
        idxs.add(round(k * (n - 1) / (cap - 1)))
    return sorted(idxs)


def growth_series(session, cap: int = GROWTH_CAP) -> list[dict]:
    """Downsampled cumulative-tokens series for the re-billing curve (US2 / research D4).

    <= ``cap`` GrowthPoints, first and last turn always preserved, cumulative and
    non-decreasing per type; the final point equals the session totals.
    """
    usages = session.turn_usages
    n = len(usages)
    if n == 0:
        return []
    ci = co = cw = cr = 0
    cum = []
    for u in usages:
        ci += u.input
        co += u.output
        cw += u.cache_write
        cr += u.cache_read
        cum.append((ci, co, cw, cr))
    out = []
    for i in _sample_indices(n, cap):
        c = cum[i]
        out.append({"i": i, "cum_input": c[0], "cum_output": c[1],
                    "cum_write": c[2], "cum_read": c[3]})
    return out


def by_day_buckets(sessions, proj_i: dict, day_i: dict) -> list[dict]:
    """Per-(project, day) token totals for the over-time trend (US3 / research D5).

    Each turn is bucketed by **its own** timestamp day (not the session's), so a long
    multi-day session is spread correctly. Indices reference the shared ``dims`` tables.
    """
    agg: dict[tuple, dict] = {}
    for s in sessions:
        p = proj_i[s.project]
        for u in s.turn_usages:
            d = day_i[day_of(u.ts) or "undated"]
            add_usage(agg.setdefault((p, d), empty_totals()), u)
    out = []
    for (p, d), t in agg.items():
        out.append({"p": p, "d": d, "input": t["input"], "output": t["output"],
                    "cache_write": t["cache_write"], "cache_read": t["cache_read"]})
    return out


def sum_by_model(session_flows: list[dict]) -> dict:
    """Sum per-model FlowTotals across sessions — the full-dataset basis for the cost estimate."""
    out: dict[str, dict] = {}
    for sf in session_flows:
        for model, t in sf.get("by_model", {}).items():
            acc = out.setdefault(model, empty_totals())
            for k in FLOW_KEYS:
                acc[k] += t[k]
    return out
