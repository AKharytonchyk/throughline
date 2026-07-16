import unittest

from throughline.analysis import timeline as tl


class TestTimeline(unittest.TestCase):
    def test_day_of(self):
        self.assertEqual(tl.day_of("2026-07-08T10:00:00Z"), "2026-07-08")
        self.assertEqual(tl.day_of("2026-07-08T23:30:00+00:00"), "2026-07-08")
        self.assertIsNone(tl.day_of(None))
        self.assertIsNone(tl.day_of("not-a-date"))

    def test_week_of_is_monday(self):
        # 2026-07-08 is a Wednesday -> week start Monday 2026-07-06
        self.assertEqual(tl.week_of("2026-07-08"), "2026-07-06")

    def test_span_and_granularity(self):
        short = ["2026-07-01", "2026-07-08"]          # 8-day span
        long = ["2026-07-01", "2026-08-01"]           # ~32-day span
        self.assertEqual(tl.span_days(short), 8)
        self.assertEqual(tl.choose_granularity(short), "day")
        self.assertEqual(tl.choose_granularity(long), "week")

    def test_bucket_of(self):
        self.assertEqual(tl.bucket_of("2026-07-08", "day"), "2026-07-08")
        self.assertEqual(tl.bucket_of("2026-07-08", "week"), "2026-07-06")


if __name__ == "__main__":
    unittest.main()
