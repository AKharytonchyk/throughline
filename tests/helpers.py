from pathlib import Path

FIX = Path(__file__).resolve().parent / "fixtures"
PROJ = FIX / "proj-demo"
TRENDS = FIX / "trends"
TOKENS = FIX / "tokens"


def parse_fixtures(size_unit="chars"):
    from throughline.parser.transcript import parse_transcript
    return [parse_transcript(p, size_unit) for p in sorted(PROJ.glob("*.jsonl"))]


def parse_token_fixtures(size_unit="chars"):
    from throughline.parser.transcript import parse_transcript
    return [parse_transcript(p, size_unit) for p in sorted(TOKENS.glob("*/*.jsonl"))]


def parse_trends(size_unit="chars"):
    from throughline.parser.transcript import parse_transcript
    return [parse_transcript(p, size_unit) for p in sorted(TRENDS.glob("*/*.jsonl"))]


def mk_call(name, iv=(), ov=(), size=100, bucket="builtin", server=None, tool=None,
            is_sidechain=False, index=0):
    from throughline.parser.transcript import ToolCall
    return ToolCall(
        session_id="s", index=index, tool_use_id=f"t{index}", name=name, bucket=bucket,
        server=server, tool=tool, input_size=size, output_size=size,
        is_sidechain=is_sidechain, input_values=set(iv), output_values=set(ov),
    )


def mk_session(calls):
    from throughline.parser.transcript import ParsedSession
    s = ParsedSession(session_id="s", project="p", path="x")
    s.tool_calls = calls
    return s
