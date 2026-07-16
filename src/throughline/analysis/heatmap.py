"""View 2 — tool heatmap: every invoked tool on frequency x volume axes (FR-016..018).

Essentialness shading (survival) is attached by the survival module when available; when
not, cells still render on both axes with no fabricated split.
"""
from __future__ import annotations


def build_heatmap(sessions: list, survival: dict | None = None) -> list[dict]:
    freq: dict[str, int] = {}
    vol: dict[str, int] = {}
    for sess in sessions:
        for c in sess.main_thread_calls():
            freq[c.key] = freq.get(c.key, 0) + 1
            vol[c.key] = vol.get(c.key, 0) + c.input_size + c.output_size

    cells: list[dict] = []
    survival = survival or {}
    for key in sorted(freq, key=lambda k: (vol[k], freq[k]), reverse=True):
        cell = {"tool_key": key, "call_count": freq[key], "total_size": vol[key]}
        s = survival.get(("tool", key))
        if s is not None:
            cell["survival"] = {
                "available": s.get("available", False),
                "rate": s.get("rate"),
                "method": s.get("method"),
            }
        cells.append(cell)
    return cells
