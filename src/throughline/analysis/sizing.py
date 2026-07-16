"""Sizing: the per-tool resident (schema) estimate and main-thread window totals.

Per-call and non-tool sizes are EXACT (measured in the parser). The resident cost is a
labeled ESTIMATE (research.md D7): total overhead R comes from the first request's cached
prefix (system prompt + schemas), an estimated system-prompt constant S is removed, and the
remaining schema overhead is distributed across the mounted tool set with a disclosed
heuristic weight. Everything resident is flagged is_estimate and states its method.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from throughline.config import Config
from throughline.parser.mounted import MountedTool
from throughline.parser.transcript import ParsedSession, ToolCall

RESIDENT_METHOD = (
    "estimate: R = first-request cache_creation_input_tokens x chars_per_token "
    "(system prompt + tool schemas); minus estimated system-prompt constant S; the "
    "remaining schema overhead is split across mounted tools by a heuristic weight "
    "(name length + observed input-shape complexity). Per-tool split is heuristic."
)


@dataclass
class ResidentEstimate:
    session_id: str
    total_overhead_size: int  # R (system prompt + schemas)
    system_prompt_size: int  # S
    per_tool: dict = field(default_factory=dict)  # mounted tool key -> est schema size
    method: str = RESIDENT_METHOD
    is_estimate: bool = True


def _tool_key(mt: MountedTool) -> str:
    # MountedTool.name is already "mcp:server/tool" (tool-level) or "mcp:server"
    # (server-level); built-ins are bare. Match ToolCall.key exactly.
    return f"builtin:{mt.name}" if mt.bucket == "builtin" else mt.name


def _observed_input_weight(calls: list[ToolCall], key_matcher) -> float:
    sizes = [c.input_size for c in calls if key_matcher(c)]
    if not sizes:
        return 0.0
    return min(sum(sizes) / len(sizes), 2000.0)  # capped avg input size as a schema proxy


def resident_estimate(
    session: ParsedSession, mounted: list[MountedTool], cfg: Config
) -> ResidentEstimate:
    R = int(round(session.resident_tokens * cfg.chars_per_token))
    S = min(cfg.system_prompt_chars, R) if R else 0
    schema_overhead = max(R - S, 0)

    calls = session.main_thread_calls()

    def matcher_for(mt: MountedTool):
        key = _tool_key(mt)
        if mt.bucket == "mcp" and "/" in mt.name:  # tool-level
            return lambda c: c.key == key
        if mt.bucket == "mcp":  # server-level
            return lambda c: c.bucket == "mcp" and c.server == mt.server
        return lambda c: c.bucket == "builtin" and c.name == mt.name

    weights: dict[str, float] = {}
    for mt in mounted:
        key = _tool_key(mt)
        w = float(len(mt.name)) + _observed_input_weight(calls, matcher_for(mt))
        weights[key] = weights.get(key, 0.0) + w

    total_w = sum(weights.values()) or 1.0
    per_tool = {
        key: int(round(schema_overhead * (w / total_w))) for key, w in weights.items()
    }
    return ResidentEstimate(
        session_id=session.session_id,
        total_overhead_size=R,
        system_prompt_size=S,
        per_tool=per_tool,
    )


def per_call_total(session: ParsedSession) -> int:
    return sum(c.input_size + c.output_size for c in session.main_thread_calls())


def sidechain_total(session: ParsedSession) -> int:
    side_calls = sum(
        c.input_size + c.output_size for c in session.tool_calls if c.is_sidechain
    )
    return session.sidechain_size + side_calls


def main_thread_total(session: ParsedSession, resident: ResidentEstimate) -> int:
    """The whole main-thread window: resident (once) + per-call + non-tool content."""
    return resident.total_overhead_size + per_call_total(session) + session.non_tool_size
