import tempfile
import unittest
from pathlib import Path

from helpers import parse_trends
from throughline.parser.transcript import parse_transcript


class TestModeTimeline(unittest.TestCase):
    def setUp(self):
        self.sessions = {s.session_id: s for s in parse_trends()}

    def test_mode_from_file_order(self):
        s1 = self.sessions["s1"]  # permission-mode auto, then Reads
        self.assertTrue(all(c.mode == "auto" for c in s1.main_thread_calls()))
        s2 = self.sessions["s2"]  # permission-mode plan
        self.assertTrue(all(c.mode == "plan" for c in s2.main_thread_calls()))

    def test_mid_session_mode_change_splits_calls(self):
        s4 = self.sessions["s4"]  # auto (Read) -> plan (Bash)
        by_name = {c.name: c.mode for c in s4.main_thread_calls()}
        self.assertEqual(by_name["Read"], "auto")
        self.assertEqual(by_name["Bash"], "plan")

    def test_unknown_before_first_mode_record(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.jsonl"
            p.write_text(
                '{"type":"assistant","sessionId":"x","timestamp":"2026-07-01T00:00:00Z",'
                '"message":{"role":"assistant","content":[{"type":"tool_use","id":"t1",'
                '"name":"Read","input":{"file_path":"/a"}}]}}\n'
            )
            sess = parse_transcript(p)
            self.assertEqual(sess.tool_calls[0].mode, "unknown")


if __name__ == "__main__":
    unittest.main()
