"""Lightweight tests for csv-insights (standard-library unittest, no deps)."""

import unittest

import csv_insights as ci


class TypeInferenceTests(unittest.TestCase):
    def test_integer_column(self):
        self.assertEqual(ci.infer_type(["1", "2", "3"]), "integer")

    def test_float_column(self):
        self.assertEqual(ci.infer_type(["1.5", "2", "3"]), "float")

    def test_text_column(self):
        self.assertEqual(ci.infer_type(["a", "b", "1"]), "text")

    def test_empty_column(self):
        self.assertEqual(ci.infer_type(["", "  ", ""]), "empty")


class ProfileTests(unittest.TestCase):
    def test_numeric_stats_and_missing(self):
        prof = ci.profile_column("age", ["10", "20", "", "30"])
        self.assertEqual(prof.dtype, "integer")
        self.assertEqual(prof.missing, 1)
        self.assertEqual(prof.unique, 3)
        self.assertEqual(prof.fill_rate, 75.0)
        self.assertEqual(prof.stats["min"], 10.0)
        self.assertEqual(prof.stats["max"], 30.0)
        self.assertEqual(prof.stats["mean"], 20.0)

    def test_top_values_for_text(self):
        prof = ci.profile_column("city", ["A", "A", "B", "C"], top=2)
        self.assertEqual(prof.top_values[0], {"value": "A", "count": 2})
        self.assertEqual(len(prof.top_values), 2)

    def test_top_zero_disables_top_values(self):
        prof = ci.profile_column("city", ["A", "B"], top=0)
        self.assertEqual(prof.top_values, [])


class RaggedRowTests(unittest.TestCase):
    def test_short_rows_are_padded(self):
        header = ["a", "b", "c"]
        data = [["1", "2"], ["3", "4", "5"]]  # first row is short
        profiles = ci.build_profiles(header, data)
        # column "c" should have one missing value from the short row
        self.assertEqual(profiles[2].missing, 1)


if __name__ == "__main__":
    unittest.main()
