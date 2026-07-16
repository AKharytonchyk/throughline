"""Attribute a tool call to a source bucket (research.md D5).

- MCP tools are named ``mcp__<server>__<tool>`` -> MCP bucket, grouped by server then tool.
- Bare names (Bash, Read, Grep, ...) -> built-in bucket, each named individually.
- CLI-wrapped MCP: a ``Bash`` command that invokes an MCP client (e.g. a ``tools-call``
  against ``@server``) is re-attributed to the MCP bucket so it is not miscounted as Bash.
- Anything unresolved -> the explicit "unattributed" bucket (FR-014).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Conservative detector for a Bash command that wraps an MCP client call. Requires BOTH an
# mcp-client indicator and a tools-call indicator to avoid false positives on ordinary Bash.
_MCP_CLIENT = re.compile(r"\bmcp[\w-]*\b", re.IGNORECASE)
_TOOLS_CALL = re.compile(r"\btools[-/]?call\b", re.IGNORECASE)
_SERVER_AT = re.compile(r"@([A-Za-z0-9][\w.-]*)")
_SERVER_FLAG = re.compile(r"--server[= ]+([A-Za-z0-9][\w.-]*)")
_TOOL_FLAG = re.compile(r"--tool[= ]+([A-Za-z0-9][\w.-]*)")


@dataclass
class Attribution:
    bucket: str  # "builtin" | "mcp" | "unattributed"
    server: str | None = None
    tool: str | None = None
    cli_wrapped_from: str | None = None


def _parse_mcp_name(name: str) -> tuple[str, str] | None:
    if not name.startswith("mcp__"):
        return None
    parts = name.split("__")
    if len(parts) < 3:
        return None
    server = parts[1]
    tool = "__".join(parts[2:])
    if not server or not tool:
        return None
    return server, tool


def detect_cli_wrapped_mcp(command: str) -> tuple[str | None, str | None] | None:
    """Return (server, tool) if a Bash command looks like an MCP-client tools-call, else None.
    Either field may be None when not extractable (server-level attribution still applies)."""
    if not command:
        return None
    if not (_MCP_CLIENT.search(command) and _TOOLS_CALL.search(command)):
        return None
    server = None
    m = _SERVER_AT.search(command) or _SERVER_FLAG.search(command)
    if m:
        server = m.group(1)
    tool = None
    mt = _TOOL_FLAG.search(command)
    if mt:
        tool = mt.group(1)
    return server, tool


def attribute(name: str, tool_input: object) -> Attribution:
    mcp = _parse_mcp_name(name or "")
    if mcp:
        return Attribution(bucket="mcp", server=mcp[0], tool=mcp[1])

    if name == "Bash" and isinstance(tool_input, dict):
        command = tool_input.get("command") or ""
        wrapped = detect_cli_wrapped_mcp(command)
        if wrapped is not None:
            server, tool = wrapped
            return Attribution(
                bucket="mcp", server=server, tool=tool, cli_wrapped_from="Bash"
            )

    if name:
        return Attribution(bucket="builtin")
    return Attribution(bucket="unattributed")
