import tempfile
import unittest
from pathlib import Path

from helpers import parse_fixtures
from throughline.parser.transcript import parse_transcript


class TestParser(unittest.TestCase):
    def setUp(self):
        self.sessions = {s.session_id: s for s in parse_fixtures()}
        self.a = self.sessions["session-a"]

    def test_ordering_is_sequential(self):
        idx = [c.index for c in self.a.tool_calls]
        self.assertEqual(idx, sorted(idx))
        self.assertEqual(idx[0], 1)

    def test_tool_use_result_pairing(self):
        get_sprint = next(c for c in self.a.tool_calls if c.name == "mcp__acme__getSprint")
        self.assertGreater(get_sprint.input_size, 0)
        self.assertGreater(get_sprint.output_size, 0)  # result paired

    def test_sidechain_tagging(self):
        grep = next(c for c in self.a.tool_calls if c.name == "Grep")
        self.assertTrue(grep.is_sidechain)
        self.assertNotIn(grep, self.a.main_thread_calls())

    def test_attachment_counts_as_non_tool(self):
        self.assertGreater(self.a.non_tool_size, 0)

    def test_resident_tokens_captured(self):
        self.assertEqual(self.a.resident_tokens, 1200)

    def test_compaction_detected(self):
        self.assertTrue(self.a.has_compaction)
        self.assertIn("TEAM-7", self.a.post_compaction_text)

    def test_compaction_metadata_captured(self):
        self.assertTrue(self.a.compaction_events)
        ev = self.a.compaction_events[0]
        self.assertEqual((ev["pre_tokens"], ev["post_tokens"]), (5000, 1500))
        self.assertIn("mcp__acme__getSprint", self.a.discovered_tools)
        self.assertTrue(self.a.compaction_summaries)  # post side is the isCompactSummary record

    def test_malformed_line_tolerated(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "bad.jsonl"
            p.write_text('{"type":"system","subtype":"x"}\nNOT JSON\n')
            sess = parse_transcript(p)
            self.assertGreaterEqual(sess.parse_warnings, 1)


if __name__ == "__main__":
    unittest.main()
