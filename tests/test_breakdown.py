import unittest

from helpers import parse_fixtures, FIX
from throughline.analysis.breakdown import aggregate_breakdown
from throughline.config import Config
from throughline.parser.mounted import build_mounted_set


class TestBreakdown(unittest.TestCase):
    def setUp(self):
        self.sessions = parse_fixtures()
        self.cfg = Config(mcp_config_paths=[str(FIX / "mcp_config.json")])
        self.mounted = build_mounted_set(self.cfg.mcp_config_paths)
        self.bd = aggregate_breakdown(self.sessions, self.mounted, self.cfg)

    def test_buckets_sum_to_main_thread_total(self):  # SC-006
        total = self.bd["main_thread_total"]
        self.assertEqual(sum(b["total_size"] for b in self.bd["breakdown"]), total)

    def test_explicit_unattributed_and_non_tool_present(self):
        keys = {b["key"] for b in self.bd["breakdown"]}
        self.assertIn("non_tool", keys)
        self.assertIn("unattributed", keys)

    def test_resident_flagged_estimate(self):
        resident = [b for b in self.bd["breakdown"] if b["kind"] == "resident"]
        self.assertTrue(resident and all(b["is_estimate"] for b in resident))

    def test_mounted_but_unused_present(self):
        by_key = {b["key"]: b for b in self.bd["breakdown"]}
        # a declared-but-unused MCP server, and a never-called built-in
        self.assertEqual(by_key["mcp:playwright"]["call_count"], 0)
        self.assertEqual(by_key["builtin:Write"]["call_count"], 0)

    def test_sidechain_excluded_from_total(self):
        self.assertGreater(self.bd["sidechain"]["size"], 0)
        # sidechain size is not part of any main-thread bucket
        keys = {b["key"] for b in self.bd["breakdown"]}
        self.assertNotIn("sidechain", keys)


if __name__ == "__main__":
    unittest.main()
