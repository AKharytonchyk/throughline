#!/usr/bin/env python3
"""Generate the fully SYNTHETIC demo dataset behind the hosted dashboard + screenshots.

Everything here is invented: a fake org 'orbit' (repos web/api/workers) and fake MCP
servers 'jira'/'browser'/'figma'. No real paths, names, transcripts, or usage. The working
dir's config overrides ``mcp_config_paths`` so the real ``~/.claude.json`` is never read.
Deterministic (seeded), so the demo is reproducible.

Usage:
    DEMO_WD=/tmp/thl-demo python3 scripts/gen_demo.py
    PYTHONPATH=src python3 -m throughline --working-dir /tmp/thl-demo \\
        report --transcript-dir /tmp/thl-demo/transcripts --out docs/index.html
"""
import json
import os
import random
import shutil
from pathlib import Path

random.seed(7)  # deterministic

WD = Path(os.environ.get("DEMO_WD", "/tmp/thl-demo"))
TR = WD / "transcripts"
if WD.exists():
    shutil.rmtree(WD)
TR.mkdir(parents=True)

# mocked repos: dir name -> project is parent.name.replace('-','/'),
# so segments must not contain internal hyphens.
REPOS = {
    "-Users-dev-code-orbit-web": "orbit/web",
    "-Users-dev-code-orbit-api": "orbit/api",
    "-Users-dev-code-orbit-workers": "orbit/workers",
}
REPO_DIRS = list(REPOS.keys())

MCP_TOOLS = [
    "mcp__jira__getIssue", "mcp__jira__listIssues",
    "mcp__jira__getSprint", "mcp__jira__searchIssues",
    "mcp__browser__navigate", "mcp__browser__snapshot", "mcp__browser__click",
]
BUILTINS = ["Read", "Grep", "Edit", "Bash", "Glob", "Write", "TodoWrite", "Task"]


def pad(token: str, n: int) -> str:
    """A content blob of ~n chars that embeds `token` (for chain linking)."""
    n = max(n, len(token) + 8)
    filler = ("lorem ipsum dolor sit amet consectetur " * ((n // 39) + 1))[: n - len(token) - 1]
    return token + " " + filler


def rec_perm(sid, mode):
    return {"type": "permission-mode", "sessionId": sid, "permissionMode": mode}


def rec_tool(sid, ts, tid, name, inp, usage=None, model=None):
    msg = {"role": "assistant", "content": [{"type": "tool_use", "id": tid, "name": name, "input": inp}]}
    if model:
        msg["model"] = model
    if usage:
        msg["usage"] = usage
    return {"type": "assistant", "sessionId": sid, "timestamp": ts, "message": msg}


def rec_text(sid, ts, text, usage=None, model=None):
    msg = {"role": "assistant", "content": [{"type": "text", "text": text}]}
    if model:
        msg["model"] = model
    if usage:
        msg["usage"] = usage
    return {"type": "assistant", "sessionId": sid, "timestamp": ts, "message": msg}


def rec_result(sid, ts, tid, content):
    return {"type": "user", "sessionId": sid, "timestamp": ts,
            "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": tid, "content": content}]}}


def rec_compact(sid, ts, pre, post, discovered):
    return {"type": "system", "subtype": "compact_boundary", "sessionId": sid, "timestamp": ts,
            "compactMetadata": {"preTokens": pre, "postTokens": post,
                                "preCompactDiscoveredTools": discovered}}


# intervention date: Read cost drops afterwards (the "did my optimization work" story)
OPT_DATE = "2026-05-18"


def read_size(day: str) -> int:
    # big before the offset/limit intervention, small after
    return random.randint(12000, 22000) if day < OPT_DATE else random.randint(2500, 6500)


def ts_for(day: str, seq: int) -> str:
    h = 9 + seq // 6
    m = (seq * 7) % 60
    return f"{day}T{h:02d}:{m:02d}:{(seq * 13) % 60:02d}Z"


# spread days across ~6 weeks
def days_in_week(monday_offset):
    base = 4  # 2026-05-04 is a Monday
    start = base + monday_offset * 7
    out = []
    for d in range(5):  # weekdays
        dd = start + d
        month, day = 5, dd
        if dd > 31:
            month, day = 6, dd - 31
        out.append(f"2026-{month:02d}-{day:02d}")
    return out


SESSIONS = []
sid_n = 0
MODES = ["auto", "plan", "acceptEdits", "auto", "plan"]
for wk in range(6):
    wdays = days_in_week(wk)
    for _ in range(random.choice([4, 5, 5])):
        sid_n += 1
        SESSIONS.append({
            "sid": f"s{sid_n}",
            "repo": REPO_DIRS[sid_n % len(REPO_DIRS)],
            "day": random.choice(wdays),
            "mode": MODES[sid_n % len(MODES)],
            "with_compact": (sid_n == 6),          # one session shows a compaction event
            "model": "claude-sonnet-5" if sid_n % 4 == 0 else "claude-opus-4-8",
        })


def build_session(s):
    sid, day, mode, model = s["sid"], s["day"], s["mode"], s["model"]
    recs = [rec_perm(sid, mode)]
    seq = 0
    ctx = [0]        # running resident context (tokens) that gets re-billed as cache_read each turn
    first = [True]

    def next_usage(added=0):
        """Advance the per-turn token flow. First turn writes the resident context (system
        prompt + tool schemas); every later turn RE-READS the whole accumulated context
        (cache_read) — which is why cache_read dominates real usage."""
        if first[0]:
            resident = random.randint(7000, 10500)
            ctx[0] = resident
            first[0] = False
            return {"input_tokens": random.randint(300, 900), "output_tokens": random.randint(150, 700),
                    "cache_creation_input_tokens": resident, "cache_read_input_tokens": 0}
        u = {"input_tokens": random.randint(150, 1400), "output_tokens": random.randint(120, 1200),
             "cache_creation_input_tokens": added, "cache_read_input_tokens": ctx[0]}
        ctx[0] += added
        return u

    def add_tool(name, inp, out, grow=None):
        nonlocal seq
        added = grow if grow is not None else random.randint(400, 2600)
        tid = f"{sid}-{seq}"
        recs.append(rec_tool(sid, ts_for(day, seq), tid, name, inp, next_usage(added), model))
        recs.append(rec_result(sid, ts_for(day, seq), tid, out))
        seq += 1

    def add_text(marker, lo, hi):
        nonlocal seq
        recs.append(rec_text(sid, ts_for(day, seq), pad(marker, random.randint(lo, hi)),
                             next_usage(random.randint(200, 1200)), model))
        seq += 1

    add_text("PLAN-note", 800, 3200)   # opening context / plan text (non-tool content)

    # a recurring, data-dependent chain: Grep -> Read -> Edit (linked by shared tokens)
    for _ in range(random.randint(1, 2)):
        n = random.randint(1000, 9999)
        file_tok = f"src/orbit/handler_{n}.py"
        sym_tok = f"SYM-{n}"
        add_tool("Grep", {"pattern": f"TASK-{n}", "path": "src/"},
                 pad(f"match in {file_tok}", random.randint(800, 2600)))
        add_tool("Read", {"file_path": file_tok, "limit": 200},
                 pad(f"def thing(): return {sym_tok}", read_size(day)))
        add_tool("Edit", {"file_path": file_tok, "old_string": sym_tok, "new_string": f"{sym_tok}_v2"},
                 pad("edit applied ok", random.randint(500, 1500)))

    for _ in range(random.randint(16, 34)):
        if random.random() < 0.35:      # interleaved reasoning (non-tool content)
            add_text("reasoning", 300, 2400)
        t = random.choices(
            ["Read", "Grep", "Bash", "Glob", "Edit", "Write", "TodoWrite", "jira", "browser"],
            weights=[34, 16, 12, 6, 10, 5, 5, 8, 6])[0]
        if t == "Read":
            add_tool("Read", {"file_path": f"src/orbit/mod_{random.randint(1, 80)}.py", "limit": 150},
                     pad("file contents", read_size(day)))
        elif t == "Grep":
            add_tool("Grep", {"pattern": "TODO|FIXME", "path": "src/"},
                     pad("grep hits", random.randint(500, 3200)))
        elif t == "Bash":
            add_tool("Bash", {"command": "pytest -q"},
                     pad("test output", random.randint(300, 3600)))
        elif t == "Glob":
            add_tool("Glob", {"pattern": "**/*.py"},
                     pad("path list", random.randint(200, 1200)))
        elif t == "Edit":
            add_tool("Edit", {"file_path": f"src/orbit/mod_{random.randint(1, 80)}.py",
                              "old_string": "a", "new_string": "b"},
                     pad("edited", random.randint(600, 5000)))
        elif t == "Write":
            add_tool("Write", {"file_path": f"src/orbit/new_{random.randint(1, 40)}.py", "content": "..."},
                     pad("written", random.randint(800, 4000)))
        elif t == "TodoWrite":
            add_tool("TodoWrite", {"todos": ["a", "b", "c"]},
                     pad("todos updated", random.randint(200, 800)))
        elif t == "jira":
            tool = random.choice(["getIssue", "listIssues", "getSprint", "searchIssues"])
            add_tool(f"mcp__jira__{tool}", {"key": f"ORB-{random.randint(100, 999)}"},
                     pad("ticket json", random.randint(1500, 12000)), grow=random.randint(600, 2400))
        elif t == "browser":
            tool = random.choice(["navigate", "snapshot", "click"])
            sz = random.randint(9000, 38000) if tool == "snapshot" else random.randint(400, 2500)
            add_tool(f"mcp__browser__{tool}", {"ref": f"e{random.randint(1, 50)}"},
                     pad("dom snapshot", sz), grow=(sz // 4 if tool == "snapshot" else random.randint(200, 900)))

    if s["with_compact"]:
        recs.append(rec_compact(sid, ts_for(day, seq), 168000, 43000, MCP_TOOLS + BUILTINS))
        seq += 1

    return recs


for s in SESSIONS:
    d = TR / s["repo"]
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{s['sid']}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in build_session(s)))

# mocked mcp config (jira/browser used; figma mounted-but-unused)
(WD / "mock_mcp.json").write_text(json.dumps({
    "mcpServers": {"jira": {"command": "x"}, "browser": {"command": "y"}, "figma": {"command": "z"}}
}, indent=2))

# working-dir config: override mcp_config_paths so the real ~/.claude.json is NEVER read
(WD / "config.json").write_text(json.dumps({
    "working_dir": str(WD),
    "size_unit": "chars",
    "chars_per_token": 4.0,
    "mcp_config_paths": [str(WD / "mock_mcp.json")],
}, indent=2))

# mocked interventions -> markers on the trends
(WD / "interventions.json").write_text(json.dumps([
    {"date": OPT_DATE, "label": "added Read offset/limit"},
    {"date": "2026-06-01", "label": "switched to plan mode"},
], indent=2))

print(f"sessions: {len(SESSIONS)}  transcripts under: {TR}")
print("repos:", ", ".join(REPOS.values()))
