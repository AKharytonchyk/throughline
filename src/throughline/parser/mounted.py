"""The mounted-tool set, including tools that were never called (research.md D7b).

Two offline sources, best first:
  1. ``preCompactDiscoveredTools`` from a compaction boundary — the REAL tool list Claude
     Code had mounted, at MCP-*tool* granularity (e.g. ``mcp__server__tool``). Preferred.
  2. A known built-in list + MCP *servers* declared in local Claude Code config
     (``~/.claude.json`` / project ``.mcp.json``) — server granularity for MCP.

Never the network, never the transcript's called-tools alone.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from throughline.parser.attribution import attribute

BUILTIN_TOOLS_VERSION = "claude-code-2.x (2026-07)"
BUILTIN_TOOLS = [
    "Bash", "Read", "Write", "Edit", "Glob", "Grep", "WebFetch", "WebSearch",
    "Task", "NotebookEdit", "TodoWrite", "BashOutput", "KillShell", "SlashCommand",
]


@dataclass
class MountedTool:
    name: str
    bucket: str  # builtin | mcp
    server: str | None = None
    source: str = "observed"  # builtin_list | mcp_config | discovered | observed
    granularity: str = "tool"  # tool | server


def read_mcp_servers(config_paths: list[str]) -> set[str]:
    """Read declared MCP server names from local config files (read-only). Never network."""
    servers: set[str] = set()
    for raw in config_paths:
        path = Path(raw).expanduser()
        if not path.exists() or not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        except (json.JSONDecodeError, OSError):
            continue
        servers |= _servers_from(data)
    return servers


def _servers_from(data: object) -> set[str]:
    out: set[str] = set()
    if not isinstance(data, dict):
        return out
    if isinstance(data.get("mcpServers"), dict):
        out |= set(data["mcpServers"].keys())
    projects = data.get("projects")
    if isinstance(projects, dict):
        for cfg in projects.values():
            if isinstance(cfg, dict) and isinstance(cfg.get("mcpServers"), dict):
                out |= set(cfg["mcpServers"].keys())
    return out


def build_mounted_set(config_paths: list[str], discovered_tools: set | None = None) -> list[MountedTool]:
    tools: dict[str, MountedTool] = {}

    # 1. known built-in tools
    for n in BUILTIN_TOOLS:
        tools[f"builtin:{n}"] = MountedTool(
            name=n, bucket="builtin", source="builtin_list", granularity="tool")

    # 2. real discovered tools (preferred; MCP at tool granularity)
    for raw in sorted(discovered_tools or []):
        attr = attribute(raw, None)
        if attr.bucket == "mcp":
            key = f"mcp:{attr.server}/{attr.tool}"
            tools[key] = MountedTool(name=key, bucket="mcp", server=attr.server,
                                     source="discovered", granularity="tool")
        else:
            tools.setdefault(f"builtin:{raw}", MountedTool(
                name=raw, bucket="builtin", source="discovered", granularity="tool"))

    covered_servers = {t.server for t in tools.values() if t.bucket == "mcp"}

    # 3. config-declared MCP servers (server granularity) — only where not already covered
    for server in sorted(read_mcp_servers(config_paths)):
        if server in covered_servers:
            continue
        tools[f"mcp:{server}"] = MountedTool(name=f"mcp:{server}", bucket="mcp",
                                             server=server, source="mcp_config",
                                             granularity="server")
    return list(tools.values())
