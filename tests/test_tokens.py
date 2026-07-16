"""Token-flow analysis tests (feature 003), incl. the SC-002 reconciliation GOLDEN test."""
import unittest

from helpers import parse_token_fixtures, TOKENS
from throughline.analysis import tokens as tk
from throughline.analysis.timeline import choose_granularity
from throughline.config import Config
from throughline.parser.mounted import build_mounted_set
from throughline.parser.transcript import parse_transcript
from throughline.report.aggregate import build_embedded_data

FLOW_KEYS = ("input", "output", "cache_write", "cache_read")


def _raw_sum(session):
    """Independently sum a session's per-turn usage — the reference the flow must reconcile to."""
    acc = {k: 0 for k in FLOW_KEYS}
    for u in session.turn_usages:
        acc["input"] += u.input
        acc["output"] += u.output
        acc["cache_write"] += u.cache_write
        acc["cache_read"] += u.cache_read
    return acc


class TestReconciliationGolden(unittest.TestCase):
    """SC-002 / FR-009: token-type totals reconcile to summed per-turn usage, zero discrepancy;
    the per-model split sums back to the session totals."""

    def setUp(self):
        self.sessions = parse_token_fixtures()

    def test_totals_reconcile_to_per_turn_usage(self):
        self.assertTrue(self.sessions)
        for s in self.sessions:
            flow = tk.session_flow(s)
            self.assertEqual(flow["totals"], _raw_sum(s), f"totals mismatch for {s.session_id}")

    def test_by_model_sums_back_to_totals(self):
        for s in self.sessions:
            flow = tk.session_flow(s)
            summed = {k: 0 for k in FLOW_KEYS}
            for totals in flow["by_model"].values():
                for k in FLOW_KEYS:
                    summed[k] += totals[k]
            self.assertEqual(summed, flow["totals"], f"by_model != totals for {s.session_id}")

    def test_multimodel_session_spans_two_models(self):
        mm = next(s for s in self.sessions if s.session_id == "multimodel")
        flow = tk.session_flow(mm)
        self.assertGreaterEqual(len(flow["by_model"]), 2)
        # still reconciles across models
        summed = {k: sum(t[k] for t in flow["by_model"].values()) for k in FLOW_KEYS}
        self.assertEqual(summed, flow["totals"])


class TestCoverageAndShare(unittest.TestCase):
    """D2 / FR-005: no-usage flagging, missing-field = 0, cache-read share formula."""

    def setUp(self):
        self.sessions = parse_token_fixtures()

    def test_no_usage_session_flagged_not_dropped(self):
        nu = next(s for s in self.sessions if s.session_id == "no_usage")
        flow = tk.session_flow(nu)
        self.assertTrue(flow["no_usage"])
        self.assertEqual(flow["turns"], 0)
        self.assertGreater(nu.no_usage_turns, 0)

    def test_missing_fields_count_as_zero(self):
        pf = next(s for s in self.sessions if s.session_id == "partialfields")
        flow = tk.session_flow(pf)
        # only input_tokens present on the one usage turn; the other three are absent → 0
        self.assertEqual(flow["totals"], {"input": 100, "output": 0, "cache_write": 0, "cache_read": 0})
        self.assertFalse(flow["no_usage"])          # it HAS a usage turn → coverage present
        self.assertEqual(pf.no_usage_turns, 1)      # …plus one turn with no usage block
        self.assertIn("unknown", flow["by_model"])  # that turn carried no model id

    def test_cache_read_share(self):
        mm = next(s for s in self.sessions if s.session_id == "multimodel")
        t = tk.session_flow(mm)["totals"]
        self.assertAlmostEqual(tk.cache_read_share(t), t["cache_read"] / tk.total_of(t))
        self.assertEqual(tk.cache_read_share({"input": 0, "output": 0, "cache_write": 0, "cache_read": 0}), 0.0)


class TestGrowthSeries(unittest.TestCase):
    """D4: downsampled, first+last preserved, non-decreasing, final == totals."""

    def setUp(self):
        self.long = next(s for s in parse_token_fixtures() if s.session_id == "long")

    def test_growth_capped_and_endpoints_preserved(self):
        g = tk.growth_series(self.long)
        self.assertLessEqual(len(g), tk.GROWTH_CAP)
        self.assertEqual(g[0]["i"], 0)
        self.assertEqual(g[-1]["i"], len(self.long.turn_usages) - 1)

    def test_growth_non_decreasing(self):
        g = tk.growth_series(self.long)
        for a, b in zip(g, g[1:]):
            for k in ("cum_input", "cum_output", "cum_write", "cum_read"):
                self.assertLessEqual(a[k], b[k])

    def test_growth_final_equals_totals(self):
        g = tk.growth_series(self.long)
        totals = tk.session_flow(self.long)["totals"]
        self.assertEqual(g[-1]["cum_input"], totals["input"])
        self.assertEqual(g[-1]["cum_output"], totals["output"])
        self.assertEqual(g[-1]["cum_write"], totals["cache_write"])
        self.assertEqual(g[-1]["cum_read"], totals["cache_read"])

    def test_short_session_keeps_every_turn(self):
        mm = next(s for s in parse_token_fixtures() if s.session_id == "multimodel")
        self.assertEqual(len(tk.growth_series(mm)), len(mm.turn_usages))


class TestByDayAndBlob(unittest.TestCase):
    """D5 / FR-007: by_day reconciles to session totals; granularity chosen from the span."""

    def setUp(self):
        self.sessions = parse_token_fixtures()
        cfg = Config(mcp_config_paths=[])
        self.blob = build_embedded_data(self.sessions, build_mounted_set([]), cfg)
        self.tf = self.blob["token_flow"]

    def test_by_day_reconciles_to_sessions(self):
        by_day = {k: 0 for k in FLOW_KEYS}
        for r in self.tf["by_day"]:
            for k in FLOW_KEYS:
                by_day[k] += r[k]
        sess = {k: 0 for k in FLOW_KEYS}
        for s in self.tf["sessions"]:
            for k in FLOW_KEYS:
                sess[k] += s["totals"][k]
        self.assertEqual(by_day, sess)

    def test_granularity_chosen_from_span(self):
        # multiday spans 2026-07-10..07-12 (3 days) → daily
        days = [self.blob["dims"]["days"][r["d"]] for r in self.tf["by_day"]]
        days = [d for d in days if d != "undated"]
        self.assertEqual(choose_granularity(days), "day")

    def test_coverage_counts(self):
        self.assertEqual(self.tf["coverage"]["sessions_total"], len(self.sessions))
        self.assertEqual(self.tf["coverage"]["sessions_no_usage"], 1)  # the no_usage fixture

    def test_no_cost_without_price_list(self):
        self.assertNotIn("cost", self.tf)  # opt-in; no prices.json → no dollar figure (FR-010)


if __name__ == "__main__":
    unittest.main()
