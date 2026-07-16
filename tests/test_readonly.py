import hashlib
import tempfile
import unittest
from pathlib import Path

from helpers import PROJ, FIX
from throughline.collector import discover
from throughline.config import Config
from throughline.parser.transcript import parse_transcript
from throughline.report.model import build_report


def _hash(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


class TestReadOnly(unittest.TestCase):
    def test_source_transcripts_unchanged_after_analysis(self):  # SC-007
        src = PROJ / "session-a.jsonl"
        before = _hash(src)
        sessions = [parse_transcript(p) for p in sorted(PROJ.glob("*.jsonl"))]
        cfg = Config(mcp_config_paths=[str(FIX / "mcp_config.json")])
        build_report(sessions, cfg)
        self.assertEqual(before, _hash(src))

    def test_copy_does_not_modify_source(self):  # FR-002
        before = _hash(PROJ / "session-a.jsonl")
        refs = discover.discover_sessions(PROJ.parent)
        with tempfile.TemporaryDirectory() as d:
            discover.copy_sessions(refs, d)
        self.assertEqual(before, _hash(PROJ / "session-a.jsonl"))


if __name__ == "__main__":
    unittest.main()
