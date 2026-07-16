import unittest
from collections import defaultdict

from helpers import parse_fixtures, parse_trends, FIX
from throughline.analysis.breakdown import aggregate_breakdown
from throughline.config import Config
from throughline.parser.mounted import build_mounted_set
from throughline.report.aggregate import build_embedded_data


def _blob(sessions, mcp_config=None):
    cfg = Config(mcp_config_paths=[str(mcp_config)] if mcp_config else [])
    mounted = build_mounted_set(cfg.mcp_config_paths)
    return build_embedded_data(sessions, mounted, cfg), cfg, mounted


class TestAggregateGolden(unittest.TestCase):
    """The trust anchor: summing the full cube reproduces 001's per-call totals."""

    def setUp(self):
        self.sessions = parse_fixtures()
        self.blob, self.cfg, self.mounted = _blob(self.sessions, FIX / "mcp_config.json")
        self.bd = aggregate_breakdown(self.sessions, self.mounted, self.cfg)
        self.tool_key = [t["key"] for t in self.blob["dims"]["tools"]]

    def test_cube_sums_match_001_per_call_buckets(self):
        # group cube by tool key
        by_tool_s = defaultdict(int)
        by_tool_n = defaultdict(int)
        for c in self.blob["cube"]:
            by_tool_s[self.tool_key[c["t"]]] += c["s"]
            by_tool_n[self.tool_key[c["t"]]] += c["n"]
        per_call = {b["key"]: b for b in self.bd["breakdown"] if b["cost_kind"] == "per_call"
                    and b["kind"] in ("builtin", "mcp_tool", "unattributed")}
        for key, bucket in per_call.items():
            if bucket["call_count"] == 0:
                continue
            self.assertEqual(by_tool_s[key], bucket["total_size"], f"size mismatch {key}")
            self.assertEqual(by_tool_n[key], bucket["call_count"], f"count mismatch {key}")

    def test_cube_total_equals_per_call_total(self):
        total_cube = sum(c["s"] for c in self.blob["cube"])
        per_call_total = sum(b["total_size"] for b in self.bd["breakdown"]
                             if b["cost_kind"] == "per_call"
                             and b["kind"] in ("builtin", "mcp_tool", "unattributed"))
        self.assertEqual(total_cube, per_call_total)


class TestAggregateTrends(unittest.TestCase):
    def setUp(self):
        self.blob, *_ = _blob(parse_trends())
        self.days = self.blob["dims"]["days"]
        self.tools = [t["key"] for t in self.blob["dims"]["tools"]]
        self.modes = self.blob["dims"]["modes"]

    def _read_idx(self):
        return self.tools.index("builtin:Read")

    def test_trend_per_call_falls_while_count_rises(self):  # SC-004
        rt = self._read_idx()
        by_day = defaultdict(lambda: [0, 0])  # day -> [n, s]
        for c in self.blob["cube"]:
            if c["t"] == rt:
                by_day[self.days[c["d"]]][0] += c["n"]
                by_day[self.days[c["d"]]][1] += c["s"]
        w1 = by_day["2026-07-01"]  # 2 large Reads
        w2 = by_day["2026-07-08"]  # 4 small Reads
        self.assertGreater(w2[0], w1[0])                       # count rose
        self.assertLess(w2[1] / w2[0], w1[1] / w1[0])          # avg-per-call fell

    def test_mode_segments_both_metrics(self):  # FR-010
        by_mode = defaultdict(lambda: [0, 0, set()])  # mode -> [n, s, sessions]
        for c in self.blob["cube"]:
            m = self.modes[c["m"]]
            by_mode[m][0] += c["n"]
            by_mode[m][1] += c["s"]
            by_mode[m][2].add(c["sess"])
        auto, plan = by_mode["auto"], by_mode["plan"]
        # plan (small Reads) cheaper per call than auto (large Reads)
        self.assertLess(plan[1] / plan[0], auto[1] / auto[0])
        # a session spanning modes (s4) is counted in BOTH auto and plan
        self.assertGreaterEqual(len(auto[2]), 2)   # s1, s3, s4
        self.assertGreaterEqual(len(plan[2]), 2)   # s2, s4

    def test_chain_occurrence_filtering_by_project(self):
        projects = self.blob["dims"]["projects"]
        occ = self.blob["chain_occurrences"]
        # the Read->Bash (mod-1234) chain recurs across projA(s1) and projB(s3)
        by_chain = defaultdict(list)
        for o in occ:
            by_chain[o["chain_id"]].append(projects[o["p"]])
        recurring = [cid for cid, projs in by_chain.items() if len(projs) >= 2]
        self.assertTrue(recurring, "expected a chain with >=2 occurrences across projects")
        cid = recurring[0]
        projb_only = [o for o in occ if o["chain_id"] == cid and projects[o["p"]] == "projB"]
        self.assertLess(len(projb_only), 2)  # filtering to projB drops it below min_recurrence


if __name__ == "__main__":
    unittest.main()
