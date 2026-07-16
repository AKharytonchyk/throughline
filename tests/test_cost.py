"""Optional dollar-cost estimate tests (feature 003, US4 / FR-010): opt-in, empty by default,
unpriced models omitted (never guessed), every figure a labeled estimate."""
import json
import tempfile
import unittest
from pathlib import Path

from helpers import parse_token_fixtures
from throughline.analysis import cost
from throughline.config import Config, load_price_list
from throughline.parser.mounted import build_mounted_set
from throughline.report.aggregate import build_embedded_data


class TestCostEstimate(unittest.TestCase):
    def test_empty_or_absent_price_list_yields_no_cost(self):
        self.assertIsNone(cost.estimate({"opus": {"input": 100}}, None))
        self.assertIsNone(cost.estimate({"opus": {"input": 100}}, {}))
        self.assertIsNone(cost.estimate({"opus": {"input": 100}}, {"models": {}}))

    def test_priced_model_multiplies_tokens_by_unit_price(self):
        totals = {"opus": {"input": 1_000_000, "output": 2_000_000, "cache_write": 0, "cache_read": 0}}
        prices = {"effective": "2026-07-01", "unit": "per_million", "currency": "USD",
                  "models": {"opus": {"input": 15, "output": 75, "cache_write": 18.75, "cache_read": 1.5}}}
        c = cost.estimate(totals, prices)
        self.assertTrue(c["available"])
        opus = c["by_model"]["opus"]
        self.assertTrue(opus["priced"])
        self.assertAlmostEqual(opus["input"], 15.0)     # 1M × $15/M
        self.assertAlmostEqual(opus["output"], 150.0)   # 2M × $75/M
        self.assertAlmostEqual(opus["total"], 165.0)
        self.assertAlmostEqual(c["total"], 165.0)

    def test_per_token_unit(self):
        totals = {"opus": {"input": 10, "output": 0, "cache_write": 0, "cache_read": 0}}
        c = cost.estimate(totals, {"unit": "per_token", "models": {"opus": {"input": 0.5}}})
        self.assertAlmostEqual(c["by_model"]["opus"]["input"], 5.0)   # 10 × $0.5/token

    def test_unpriced_model_flagged_not_guessed(self):
        totals = {"opus": {"input": 100, "output": 0, "cache_write": 0, "cache_read": 0},
                  "haiku": {"input": 999, "output": 0, "cache_write": 0, "cache_read": 0}}
        c = cost.estimate(totals, {"models": {"opus": {"input": 15}}})
        self.assertFalse(c["by_model"]["haiku"]["priced"])
        self.assertNotIn("input", c["by_model"]["haiku"])   # no guessed figure for the unpriced model
        self.assertNotIn("total", c["by_model"]["haiku"])

    def test_estimate_carries_its_basis_label(self):
        c = cost.estimate({"opus": {"input": 1_000_000, "output": 0, "cache_write": 0, "cache_read": 0}},
                          {"effective": "2026-07-01", "unit": "per_million", "currency": "USD",
                           "models": {"opus": {"input": 15}}})
        self.assertEqual(c["effective"], "2026-07-01")
        self.assertIn("million", c["unit_label"])
        self.assertEqual(c["currency"], "USD")

    def test_type_unpriced_for_priced_model_is_omitted(self):
        # opus is priced but only for input; output tokens must not be guessed
        c = cost.estimate({"opus": {"input": 1_000_000, "output": 5_000_000, "cache_write": 0, "cache_read": 0}},
                          {"unit": "per_million", "models": {"opus": {"input": 15}}})
        opus = c["by_model"]["opus"]
        self.assertIn("input", opus)
        self.assertNotIn("output", opus)
        self.assertAlmostEqual(opus["total"], 15.0)


class TestPriceListLoaderAndBlob(unittest.TestCase):
    def test_absent_file_is_empty(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = Config(working_dir=d)
            self.assertEqual(load_price_list(cfg), {})

    def test_loads_file_when_present(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = Config(working_dir=d)
            cfg.working.mkdir(parents=True, exist_ok=True)
            cfg.prices_path.write_text(json.dumps({"models": {"claude-opus-4-8": {"input": 15}}}))
            self.assertIn("models", load_price_list(cfg))

    def test_blob_omits_cost_without_prices_but_includes_it_with(self):
        sessions = parse_token_fixtures()
        cfg = Config(mcp_config_paths=[])
        mounted = build_mounted_set([])
        no_cost = build_embedded_data(sessions, mounted, cfg)["token_flow"]
        self.assertNotIn("cost", no_cost)
        prices = {"unit": "per_million", "effective": "2026-07-01",
                  "models": {"claude-opus-4-8": {"input": 15, "output": 75, "cache_write": 18.75, "cache_read": 1.5}}}
        with_cost = build_embedded_data(sessions, mounted, cfg, price_list=prices)["token_flow"]
        self.assertIn("cost", with_cost)
        self.assertTrue(with_cost["cost"]["available"])
        # opus priced; the "unknown"-model turn (partialfields) is present in data but unpriced
        self.assertTrue(with_cost["cost"]["by_model"]["claude-opus-4-8"]["priced"])
        self.assertFalse(with_cost["cost"]["by_model"]["unknown"]["priced"])


if __name__ == "__main__":
    unittest.main()
