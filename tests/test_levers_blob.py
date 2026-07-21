"""Feature 005 blob additions: chars_per_token, mounted_resident (+ golden reconciliation),
and the opt-in token_flow.unit_prices gate."""
import unittest

from helpers import parse_fixtures
from throughline.analysis import sizing
from throughline.config import Config
from throughline.parser.mounted import build_mounted_set
from throughline.report.aggregate import build_embedded_data


def _mounted_for(sessions):
    discovered = set()
    for s in sessions:
        discovered |= s.discovered_tools
    return build_mounted_set([], discovered_tools=discovered)


class TestBlobAdditions(unittest.TestCase):
    def setUp(self):
        self.sessions = parse_fixtures()
        self.cfg = Config(mcp_config_paths=[])
        self.mounted = _mounted_for(self.sessions)
        self.blob = build_embedded_data(self.sessions, self.mounted, self.cfg)

    def test_chars_per_token_embedded(self):
        self.assertIn("chars_per_token", self.blob)
        self.assertEqual(self.blob["chars_per_token"], self.cfg.chars_per_token)

    def test_mounted_resident_shape(self):
        mr = self.blob["mounted_resident"]
        self.assertIsInstance(mr, list)
        self.assertGreater(len(mr), 0, "proj-demo should have mounted tools with resident")
        for row in mr:
            self.assertIn(row["key"], self.blob["mounted_keys"])
            self.assertGreaterEqual(row["resident_tokens_est"], 0)
            self.assertTrue(row["is_estimate"])
            self.assertTrue(row["method"])

    def test_mounted_resident_is_the_averaged_table(self):
        """GOLDEN: each embedded value == round(mean over sessions of per_tool[key]/chars_per_token)."""
        acc: dict[str, list] = {}
        for s in self.sessions:
            for k, sz in sizing.resident_estimate(s, self.mounted, self.cfg).per_tool.items():
                a = acc.setdefault(k, [0, 0])
                a[0] += sz
                a[1] += 1
        cpt = self.cfg.chars_per_token
        expected = {k: round((tot / cnt) / cpt) for k, (tot, cnt) in acc.items() if cnt}
        got = {r["key"]: r["resident_tokens_est"] for r in self.blob["mounted_resident"]}
        self.assertEqual(got, expected)

    def test_per_session_resident_reconciles(self):
        """Σ per-tool resident chars + system prompt ≈ total overhead (within per-tool rounding)."""
        for s in self.sessions:
            res = sizing.resident_estimate(s, self.mounted, self.cfg)
            recon = sum(res.per_tool.values()) + res.system_prompt_size
            self.assertLessEqual(abs(recon - res.total_overhead_size), max(1, len(res.per_tool)))

    def test_unit_prices_absent_without_price_list(self):
        self.assertNotIn("unit_prices", self.blob["token_flow"])  # opt-in; no prices → no $ path

    def test_unit_prices_present_with_price_list(self):
        prices = {"models": {"opus": {"cache_read": 3.0, "input": 15.0}},
                  "unit": "per_million", "currency": "USD", "effective": "2026-07-01"}
        blob = build_embedded_data(self.sessions, self.mounted, self.cfg, price_list=prices)
        up = blob["token_flow"]["unit_prices"]
        self.assertTrue(up["available"])
        self.assertEqual(up["currency"], "USD")
        self.assertTrue(up["per_million"])
        self.assertIn("opus", up["by_model"])
        self.assertEqual(up["by_model"]["opus"]["cache_read"], 3.0)


if __name__ == "__main__":
    unittest.main()
