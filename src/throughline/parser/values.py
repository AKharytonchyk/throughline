"""Extract distinctive identifier-like values from tool inputs/outputs.

Used by the sequence miner to detect a DATA DEPENDENCY (a value produced by one call's
output reappears in the next call's input). Conservative on purpose — only tokens that look
like ids / paths / quoted keys, above a length threshold, to avoid coincidental links. Only
these small extracted tokens are kept in memory; full content is not retained.
"""
from __future__ import annotations

import json
import re

_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_./:@-]{5,}")
_MAX_VALUES = 60  # cap per call to bound memory


def _distinctive(tok: str) -> bool:
    # keep tokens that look like ids/paths/keys: contain a digit or a separator
    return any(c.isdigit() for c in tok) or any(c in tok for c in "/._-:@")


def extract_values(value: object) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, str):
        text = value
    else:
        try:
            text = json.dumps(value, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            text = str(value)
    out: set[str] = set()
    for m in _TOKEN.finditer(text):
        tok = m.group(0)
        if _distinctive(tok):
            out.add(tok)
            if len(out) >= _MAX_VALUES:
                break
    return out
