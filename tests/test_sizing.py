import unittest

from helpers import parse_fixtures
from throughline.analysis import sizing
from throughline.config import Config
from throughline.parser.mounted import build_mounted_set
from helpers import FIX


class TestSizing(unittest.TestCase):
    def setUp(self):
        self.sessions = {s.session_id: s for s in parse_fixtures()}
        self.a = self.sessions["session-a"]
        self.mounted = build_mounted_set([str(FIX / "mcp_config.json")])

    def test_per_call_total_exact(self):
        # exact sum of main-thread input+output sizes
        expected = sum(c.input_size + c.output_size for c in self.a.main_thread_calls())
        self.assertEqual(sizing.per_call_total(self.a), expected)

    def test_resident_is_estimate_and_normalizes_to_overhead(self):
        cfg = Config(system_prompt_chars=1000, chars_per_token=4.0)
        est = sizing.resident_estimate(self.a, self.mounted, cfg)
        self.assertTrue(est.is_estimate)
        R = 1200 * 4  # cache_creation_input_tokens * chars_per_token
        self.assertEqual(est.total_overhead_size, R)
        schema_overhead = R - 1000
        # per-tool split sums (within rounding) to the schema overhead
        self.assertAlmostEqual(sum(est.per_tool.values()), schema_overhead, delta=len(est.per_tool))
        self.assertIn("estimate", est.method.lower())
        self.assertIn("heuristic", est.method.lower())

    def test_sidechain_separate_from_main(self):
        self.assertGreater(sizing.sidechain_total(self.a), 0)

    def test_main_thread_total_composition(self):
        cfg = Config()
        est = sizing.resident_estimate(self.a, self.mounted, cfg)
        total = sizing.main_thread_total(self.a, est)
        self.assertEqual(
            total,
            est.total_overhead_size + sizing.per_call_total(self.a) + self.a.non_tool_size,
        )


if __name__ == "__main__":
    unittest.main()
