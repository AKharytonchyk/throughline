"""Flatten a Claude Code session transcript (JSONL) into an ordered list of tool calls
plus the size accounting the analysis needs (contracts/transcript-schema.md).

Defensive by design: unknown record types are ignored, malformed lines are skipped and
counted, and partial/in-progress transcripts do not crash the run.

Compaction: the transcript retains both sides on disk. A ``system``/``compact_boundary``
record carries exact ``compactMetadata`` (pre/post tokens, the discovered tool list); the
compacted summary is the ``user`` record flagged ``isCompactSummary`` that follows it. Both
are captured here so survival can be computed from the transcript alone.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from throughline.parser.attribution import attribute
from throughline.parser.values import extract_values


def size_of(value: object, unit: str = "chars") -> int:
    """Exact content size in `unit` (chars or bytes)."""
    if value is None:
        return 0
    if isinstance(value, str):
        s = value
    else:
        s = json.dumps(value, ensure_ascii=False, default=str)
    return len(s.encode("utf-8")) if unit == "bytes" else len(s)


def _text_of_block(block: dict) -> str:
    for key in ("text", "thinking"):
        v = block.get(key)
        if isinstance(v, str):
            return v
    return ""


def _tool_result_size(block: dict, unit: str) -> int:
    content = block.get("content")
    if isinstance(content, str):
        return size_of(content, unit)
    if isinstance(content, list):
        total = 0
        for c in content:
            if isinstance(c, dict):
                total += size_of(_text_of_block(c) or c, unit)
            else:
                total += size_of(c, unit)
        return total
    return 0


@dataclass
class ToolCall:
    session_id: str
    index: int
    tool_use_id: str
    name: str
    bucket: str  # builtin | mcp | unattributed
    server: str | None = None
    tool: str | None = None
    input: object = None
    input_size: int = 0
    output_size: int = 0
    is_error: bool = False
    timestamp: str = ""
    caller: str | None = None
    is_sidechain: bool = False
    cli_wrapped_from: str | None = None
    mode: str = "unknown"  # Claude Code working mode active at this call (feature 002, D3)
    input_values: set = field(default_factory=set)
    output_values: set = field(default_factory=set)

    @property
    def key(self) -> str:
        if self.bucket == "mcp":
            return f"mcp:{self.server or '?'}/{self.tool or '?'}"
        if self.bucket == "builtin":
            return f"builtin:{self.name}"
        return "unattributed"


@dataclass
class TurnUsage:
    """Per-assistant-turn token usage read verbatim from ``message.usage`` (feature 003, D1).

    All four counts are exact reads (missing field ⇒ 0); nothing here is derived.
    """
    input: int = 0
    output: int = 0
    cache_write: int = 0
    cache_read: int = 0
    model: str = "unknown"
    ts: str | None = None


@dataclass
class ParsedSession:
    session_id: str
    project: str
    path: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    non_tool_size: int = 0  # main-thread messages/thinking/attachments (incl. compact summaries)
    sidechain_size: int = 0  # separate windows (D4) — reported apart from main total
    sidechain_calls: int = 0
    resident_tokens: int = 0  # first-request cache_creation_input_tokens (D7)
    turn_usages: list = field(default_factory=list)  # per main-thread assistant turn (feature 003)
    no_usage_turns: int = 0  # main-thread assistant turns with no usage block (flagged, not dropped)
    has_compaction: bool = False
    boundary_count: int = 0
    post_compaction_text: str = ""  # joined isCompactSummary texts (survival post-side)
    compaction_summaries: list = field(default_factory=list)
    compaction_events: list = field(default_factory=list)  # {trigger, pre_tokens, post_tokens}
    discovered_tools: set = field(default_factory=set)  # from compactMetadata (real mounted set)
    parse_warnings: int = 0

    def main_thread_calls(self) -> list[ToolCall]:
        return [c for c in self.tool_calls if not c.is_sidechain]


def parse_transcript(path: str | Path, size_unit: str = "chars") -> ParsedSession:
    p = Path(path)
    session_id = p.stem
    project = p.parent.name.replace("-", "/")
    sess = ParsedSession(session_id=session_id, project=project, path=str(p))

    pending: dict[str, ToolCall] = {}
    order = 0
    current_mode = "unknown"  # tracked by file order from permission-mode records (D3)

    for rec in _iter_records(p, sess):
        rtype = rec.get("type")
        is_side = rec.get("isSidechain") is True

        if rtype == "permission-mode":
            m = rec.get("permissionMode")
            if m:
                current_mode = m
            continue

        if rtype == "system" and rec.get("subtype") == "compact_boundary":
            sess.has_compaction = True
            sess.boundary_count += 1
            cm = rec.get("compactMetadata")
            if isinstance(cm, dict):
                sess.compaction_events.append({
                    "trigger": cm.get("trigger"),
                    "pre_tokens": int(cm.get("preTokens") or 0),
                    "post_tokens": int(cm.get("postTokens") or 0),
                })
                for t in cm.get("preCompactDiscoveredTools") or []:
                    if isinstance(t, str):
                        sess.discovered_tools.add(t)
            continue

        if rtype == "attachment":
            tgt = "sidechain_size" if is_side else "non_tool_size"
            setattr(sess, tgt, getattr(sess, tgt) + size_of(rec.get("attachment"), size_unit))
            continue

        msg = rec.get("message")
        if not isinstance(msg, dict):
            continue

        if rtype == "assistant":
            usage = msg.get("usage")
            if sess.resident_tokens == 0 and isinstance(usage, dict):
                sess.resident_tokens = int(usage.get("cache_creation_input_tokens") or 0)
            # feature 003: capture per-turn token flow for MAIN-THREAD turns only (D2).
            if not is_side:
                if isinstance(usage, dict):
                    sess.turn_usages.append(TurnUsage(
                        input=int(usage.get("input_tokens") or 0),
                        output=int(usage.get("output_tokens") or 0),
                        cache_write=int(usage.get("cache_creation_input_tokens") or 0),
                        cache_read=int(usage.get("cache_read_input_tokens") or 0),
                        model=(msg.get("model") or "unknown"),
                        ts=rec.get("timestamp") or None,
                    ))
                else:
                    sess.no_usage_turns += 1

        content = msg.get("content")
        if not isinstance(content, list):
            if isinstance(content, str):
                if rec.get("isCompactSummary"):
                    sess.compaction_summaries.append(content)
                _add_non_tool(sess, content, size_unit, is_side)
            continue

        for block in content:
            if not isinstance(block, dict):
                continue
            btype = block.get("type")
            if btype == "tool_use":
                order += 1
                name = block.get("name") or ""
                inp = block.get("input")
                attr = attribute(name, inp)
                tc = ToolCall(
                    session_id=session_id, index=order,
                    tool_use_id=block.get("id") or f"_{order}", name=name,
                    bucket=attr.bucket, server=attr.server, tool=attr.tool, input=inp,
                    input_size=size_of(inp, size_unit), timestamp=rec.get("timestamp", ""),
                    caller=block.get("caller"), is_sidechain=is_side,
                    cli_wrapped_from=attr.cli_wrapped_from, mode=current_mode,
                    input_values=extract_values(inp),
                )
                sess.tool_calls.append(tc)
                pending[tc.tool_use_id] = tc
                if is_side:
                    sess.sidechain_calls += 1
            elif btype == "tool_result":
                tid = block.get("tool_use_id")
                tc = pending.get(tid)
                sz = _tool_result_size(block, size_unit)
                if tc is None and rec.get("toolUseResult") is not None:
                    sz = sz or size_of(rec.get("toolUseResult"), size_unit)
                if tc is not None:
                    tc.output_size = sz
                    tc.is_error = bool(block.get("is_error"))
                    tc.output_values = extract_values(block.get("content"))
            elif btype in ("text", "thinking"):
                _add_non_tool(sess, _text_of_block(block), size_unit, is_side)

    sess.post_compaction_text = "\n".join(sess.compaction_summaries)
    return sess


def _add_non_tool(sess, text, unit, is_side):
    if not text:
        return
    if is_side:
        sess.sidechain_size += size_of(text, unit)
    else:
        sess.non_tool_size += size_of(text, unit)


def _iter_records(path: Path, sess: ParsedSession):
    try:
        fh = path.open("r", encoding="utf-8", errors="replace")
    except OSError:
        return
    with fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                sess.parse_warnings += 1
                continue
