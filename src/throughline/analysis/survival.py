"""Essentialness / survival estimate (US4, FR-024..026, research.md D8).

Computed from the transcript itself: the compacted summary (the ``isCompactSummary`` records)
is compared against each tool's returned content. A tool whose distinctive returned values
(ids/paths) reappear in the post-compaction summary "mattered" for that intent; content that
vanished was largely noise. This works retroactively on any compacted session — no backup or
hook required. ALWAYS a labeled ESTIMATE; "unavailable" when no compaction summary exists.

Separately, ``compactMetadata`` gives an EXACT context-retention ratio (pre/post tokens),
surfaced by the report model as an exact figure — distinct from this per-tool estimate.
"""
from __future__ import annotations

from throughline.parser.values import extract_values

SURVIVAL_METHOD = (
    "estimate: fraction of a tool's distinctive returned values (ids/paths) that reappear "
    "in the post-compaction summary; set overlap over extracted identifiers."
)


def compute_survival(sessions: list) -> tuple[dict, list[str]]:
    """Return ({(scope, key): {available, rate, method}}, warnings), from transcripts."""
    num: dict[str, float] = {}
    den: dict[str, float] = {}
    any_summary = False

    for sess in sessions:
        summary_vals = extract_values(sess.post_compaction_text)
        if not summary_vals:
            continue
        any_summary = True
        for c in sess.main_thread_calls():
            ov = c.output_values
            if not ov:
                continue
            num[c.key] = num.get(c.key, 0.0) + len(ov & summary_vals)
            den[c.key] = den.get(c.key, 0.0) + len(ov)

    if not any_summary:
        return {}, [
            "Essentialness/survival unavailable: no compaction summary found in the "
            "collected sessions (nothing has been compacted yet)."
        ]

    result: dict = {}
    for key, d in den.items():
        if d <= 0:
            continue
        result[("tool", key)] = {
            "available": True, "rate": num[key] / d, "method": SURVIVAL_METHOD,
        }
    return result, []


def chain_survival(step_keys: list[str], survival: dict) -> dict:
    """Average per-tool survival across a chain's steps; unavailable if none available."""
    rates = [survival[("tool", k)]["rate"] for k in step_keys
             if survival.get(("tool", k), {}).get("available")
             and survival[("tool", k)].get("rate") is not None]
    if not rates:
        return {"available": False, "rate": None, "method": SURVIVAL_METHOD}
    return {"available": True, "rate": sum(rates) / len(rates), "method": SURVIVAL_METHOD}
