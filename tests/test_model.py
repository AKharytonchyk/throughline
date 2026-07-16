import unittest

from helpers import parse_fixtures, FIX
from throughline.config import Config
from throughline.report.model import build_report


class TestModel(unittest.TestCase):
    def setUp(self):
        self.cfg = Config(mcp_config_paths=[str(FIX / "mcp_config.json")])
        self.rep = build_report(parse_fixtures(), self.cfg)

    def test_exact_compaction_retention(self):
        c = self.rep["compaction"]
        self.assertEqual(c["events"], 1)
        self.assertEqual((c["pre_tokens"], c["post_tokens"]), (5000, 1500))
        self.assertAlmostEqual(c["retention_pct"], 30.0)  # 1500/5000 — EXACT, from Claude Code
        self.assertTrue(c["exact"])

    def test_mcp_tool_granularity_when_discovered(self):
        self.assertEqual(self.rep["sizing"]["mcp_granularity"], "tool")
        keys = {b["key"] for b in self.rep["breakdown"]}
        # a discovered-but-never-called MCP tool now shows unused at TOOL granularity
        self.assertIn("mcp:playwright/browser_navigate", keys)

    def test_buckets_still_sum_to_total(self):
        total = self.rep["_main_thread_total"]
        self.assertEqual(sum(b["total_size"] for b in self.rep["breakdown"]), total)


if __name__ == "__main__":
    unittest.main()
