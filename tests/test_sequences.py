import unittest

from helpers import mk_call, mk_session
from throughline.analysis.sequences import mine_sequences, _is_contiguous_sub
from throughline.config import Config


class TestSequences(unittest.TestCase):
    def setUp(self):
        self.cfg = Config(min_recurrence=1)

    def test_coincidental_adjacency_rejected(self):
        # two adjacent calls with no shared output->input value: no chain
        calls = [mk_call("A", ov={"AAA-111"}, index=0),
                 mk_call("B", iv={"ZZZ-999"}, index=1)]
        chains = mine_sequences([mk_session(calls)], self.cfg)
        self.assertEqual(chains, [])

    def test_data_dependency_forms_chain(self):
        calls = [mk_call("A", ov={"SHARED-1"}, index=0),
                 mk_call("B", iv={"SHARED-1"}, index=1)]
        chains = mine_sequences([mk_session(calls)], self.cfg)
        self.assertEqual(len(chains), 1)
        self.assertEqual([s["signature"] for s in chains[0]["steps"]],
                         ["builtin:A", "builtin:B"])

    def test_fanout_collapses_to_one_step(self):
        calls = [
            mk_call("A", ov={"X-123"}, index=0),
            mk_call("B", iv={"X-123"}, index=1),
            mk_call("B", iv={"Y-456"}, index=2),  # consecutive same key -> fan-out
        ]
        chains = mine_sequences([mk_session(calls)], self.cfg)
        self.assertEqual(len(chains), 1)
        steps = chains[0]["steps"]
        self.assertEqual(len(steps), 2)
        self.assertTrue(steps[1]["fanout"])

    def test_ranked_by_score_desc(self):
        cheap = mk_session([mk_call("A", ov={"S-1"}, size=10, index=0),
                            mk_call("B", iv={"S-1"}, size=10, index=1)])
        pricey = mk_session([mk_call("C", ov={"S-2"}, size=900, index=0),
                             mk_call("D", iv={"S-2"}, size=900, index=1)])
        chains = mine_sequences([cheap, pricey], self.cfg)
        scores = [c["score"] for c in chains]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_overlapping_chains_deduped(self):
        long_s = mk_session([mk_call("A", ov={"P-1"}, index=0),
                             mk_call("B", iv={"P-1"}, ov={"Q-1"}, index=1),
                             mk_call("C", iv={"Q-1"}, index=2)])
        short_s = mk_session([mk_call("A", ov={"P-2"}, index=0),
                              mk_call("B", iv={"P-2"}, index=1)])  # A->B only
        chains = mine_sequences([long_s, short_s], self.cfg)
        sigs = [[s["signature"] for s in c["steps"]] for c in chains]
        self.assertIn(["builtin:A", "builtin:B", "builtin:C"], sigs)
        self.assertNotIn(["builtin:A", "builtin:B"], sigs)  # dropped as contiguous sub

    def test_proposal_fields_present(self):
        calls = [mk_call("A", ov={"S-1"}, index=0), mk_call("B", iv={"S-1"}, index=1)]
        chains = mine_sequences([mk_session(calls)], self.cfg)
        p = chains[0]["proposal"]
        self.assertTrue(p["suggested_name"])
        self.assertIn("inputs", p)
        self.assertTrue(p["output"])
        self.assertGreaterEqual(p["est_context_saved"], 0)

    def test_is_contiguous_sub(self):
        self.assertTrue(_is_contiguous_sub(["a", "b"], ["a", "b", "c"]))
        self.assertFalse(_is_contiguous_sub(["a", "c"], ["a", "b", "c"]))


if __name__ == "__main__":
    unittest.main()
