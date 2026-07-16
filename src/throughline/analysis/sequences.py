"""View 3 (headline) — recurring, data-dependent tool-call chains (FR-019..023, D9).

Pipeline per session: collapse fan-out runs -> link steps by output->input DATA DEPENDENCY
(skipping unrelated interleaved calls) -> extract chains. Then aggregate identical chain
shapes across sessions, de-duplicate overlapping/nested shapes, score by
``recurrence x total_cost x (1 - survival)`` (survival-unavailable => factor 1), rank, and
emit an intent-tool proposal per chain.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from throughline.analysis.survival import chain_survival


@dataclass
class Step:
    key: str
    fanout: bool
    cost: int
    last_output: int
    input_values: set = field(default_factory=set)
    output_values: set = field(default_factory=set)


def _short(key: str) -> str:
    if key.startswith("mcp:") and "/" in key:
        return key.split("/", 1)[1]
    if key.startswith("builtin:"):
        return key.split(":", 1)[1]
    return key


def _collapse_fanout(calls: list) -> list[Step]:
    steps: list[Step] = []
    i = 0
    n = len(calls)
    while i < n:
        j = i
        while j + 1 < n and calls[j + 1].key == calls[i].key:
            j += 1
        run = calls[i:j + 1]
        cost = sum(c.input_size + c.output_size for c in run)
        iv: set = set()
        ov: set = set()
        for c in run:
            iv |= c.input_values
            ov |= c.output_values
        steps.append(Step(
            key=calls[i].key, fanout=(len(run) > 1), cost=cost,
            last_output=run[-1].output_size, input_values=iv, output_values=ov,
        ))
        i = j + 1
    return steps


def _next_dependent(steps: list[Step], cur: int, used: set[int]) -> int | None:
    out = steps[cur].output_values
    if not out:
        return None
    for j in range(cur + 1, len(steps)):
        if j in used:
            continue
        if out & steps[j].input_values:
            return j
    return None


def _extract_chains(steps: list[Step]) -> list[list[int]]:
    chains: list[list[int]] = []
    used: set[int] = set()
    for i in range(len(steps)):
        if i in used:
            continue
        chain = [i]
        cur = i
        while True:
            nxt = _next_dependent(steps, cur, used)
            if nxt is None:
                break
            chain.append(nxt)
            cur = nxt
        if len(chain) >= 2:
            used.update(chain)
            chains.append(chain)
    return chains


def _is_contiguous_sub(a: list[str], b: list[str]) -> bool:
    if len(a) >= len(b):
        return False
    for start in range(len(b) - len(a) + 1):
        if b[start:start + len(a)] == a:
            return True
    return False


def mine_sequences(sessions: list, cfg, survival: dict | None = None) -> list[dict]:
    survival = survival or {}
    occurrences: dict[tuple, dict] = {}

    for sess in sessions:
        steps = _collapse_fanout(sess.main_thread_calls())
        for chain in _extract_chains(steps):
            sig = tuple((steps[k].key, steps[k].fanout) for k in chain)
            total_cost = sum(steps[k].cost for k in chain)
            last_output = steps[chain[-1]].last_output
            intermediate = max(total_cost - last_output, 0)
            agg = occurrences.setdefault(sig, {
                "costs": [], "intermediates": [], "step_keys": [steps[k].key for k in chain],
                "fanout": [steps[k].fanout for k in chain],
                "first_inputs": sorted(steps[chain[0]].input_values)[:3],
            })
            agg["costs"].append(total_cost)
            agg["intermediates"].append(intermediate)

    # recurrence threshold
    kept = {sig: agg for sig, agg in occurrences.items()
            if len(agg["costs"]) >= cfg.min_recurrence}

    # de-duplicate overlapping/nested shapes: drop a chain whose key-sequence is a
    # contiguous sub-sequence of another kept chain (keep the longer, FR-023).
    sigs = list(kept)
    drop: set[tuple] = set()
    for a in sigs:
        for b in sigs:
            if a is b:
                continue
            if _is_contiguous_sub(kept[a]["step_keys"], kept[b]["step_keys"]):
                drop.add(a)
                break

    chains: list[dict] = []
    for sig, agg in kept.items():
        if sig in drop:
            continue
        recurrence = len(agg["costs"])
        total_cost = round(sum(agg["costs"]) / recurrence)
        intermediate = round(sum(agg["intermediates"]) / recurrence)
        surv = chain_survival(agg["step_keys"], survival)
        if surv["available"] and surv["rate"] is not None:
            factor = 1.0 - surv["rate"]
            never_essential = round(intermediate * factor)
        else:
            factor = 1.0
            never_essential = None
        score = recurrence * total_cost * factor
        chains.append({
            "chain_id": hashlib.sha1(repr(sig).encode()).hexdigest()[:12],
            "steps": [{"signature": k, "fanout": f} for k, f in sig],
            "data_edges": [[i, i + 1] for i in range(len(sig) - 1)],
            "recurrence": recurrence,
            "total_cost": total_cost,
            "intermediate_never_essential": never_essential,
            "survival": surv,
            "score": round(score, 2),
            "proposal": _proposal(agg, intermediate),
        })

    chains.sort(key=lambda c: c["score"], reverse=True)
    return chains


def _proposal(agg: dict, intermediate: int) -> dict:
    shorts = [_short(k) for k in agg["step_keys"]]
    name = "_".join(shorts)[:64] if shorts else "intent_tool"
    return {
        "suggested_name": name,
        "inputs": agg["first_inputs"] or [shorts[0] + " inputs"],
        "output": shorts[-1] + " result",
        "est_context_saved": intermediate,
    }
