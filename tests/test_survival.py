import unittest

from helpers import parse_fixtures
from throughline.analysis.survival import compute_survival


class TestSurvival(unittest.TestCase):
    def test_available_from_transcript_summary(self):
        # session-a has a compact_boundary + isCompactSummary; survival is computed from
        # the transcript (no backup/hook needed) via value overlap with the summary.
        survival, warnings = compute_survival(parse_fixtures())
        self.assertEqual(warnings, [])
        key = ("tool", "mcp:acme/getSprint")
        self.assertIn(key, survival)
        self.assertTrue(survival[key]["available"])
        self.assertIsNotNone(survival[key]["rate"])
        self.assertGreater(survival[key]["rate"], 0)  # SPR-123 / TEAM-7 survive into summary
        self.assertIn("estimate", survival[key]["method"].lower())

    def test_unavailable_without_compaction(self):
        sessions = [s for s in parse_fixtures() if s.session_id == "session-b"]
        survival, warnings = compute_survival(sessions)
        self.assertEqual(survival, {})
        self.assertTrue(any("unavailable" in w.lower() for w in warnings))


if __name__ == "__main__":
    unittest.main()
