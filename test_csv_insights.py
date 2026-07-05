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
        self.assertEqual(ci.infer_type(["", " ", ""]), "empty")


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

    def test_percentiles_present_and_ordered(self):
        prof = ci.profile_column("v", ["1", "2", "3", "4", "5"])
        self.assertIn("p25", prof.stats)
        self.assertIn("p75", prof.stats)
        # p25 <= median <= p75 should always hold for numeric data
        self.assertLessEqual(prof.stats["p25"], prof.stats["median"])
        self.assertLessEqual(prof.stats["median"], prof.stats["p75"])

    def test_percentiles_single_value(self):
        prof = ci.profile_column("v", ["42"])
        self.assertEqual(prof.stats["p25"], 42.0)
        self.assertEqual(prof.stats["p75"], 42.0)

    def test_top_values_for_text(self):
        prof = ci.profile_column("city", ["A", "A", "B", "C"], top=2)
        self.assertEqual(prof.top_values[0], {"value": "A", "count": 2})
        self.assertEqual(len(prof.top_values), 2)

    def test_top_zero_disables_top_values(self):
        prof = ci.profile_column("city", ["A", "B"], top=0)
        self.assertEqual(prof.top_values, [])


class HistogramTests(unittest.TestCase):
    def test_counts_sum_to_n_and_bins_respected(self):
        nums = [float(i) for i in range(1, 101)]  # 1..100
        hist = ci.build_histogram(nums, bins=8)
        self.assertEqual(len(hist), 8)
        self.assertEqual(sum(b["count"] for b in hist), 100)
        # max value must land in the last bin, not overflow
        self.assertGreater(hist[-1]["count"], 0)

    def test_identical_values_single_bin(self):
        hist = ci.build_histogram([7.0, 7.0, 7.0], bins=8)
        self.assertEqual(len(hist), 1)
        self.assertEqual(hist[0]["count"], 3)
        self.assertEqual(hist[0]["lo"], hist[0]["hi"])

    def test_profile_histogram_opt_in(self):
        values = ["1", "2", "3", "4"]
        self.assertEqual(ci.profile_column("v", values).histogram, [])
        prof = ci.profile_column("v", values, bins=4)
        self.assertEqual(len(prof.histogram), 4)
        self.assertEqual(sum(b["count"] for b in prof.histogram), 4)


class OutlierTests(unittest.TestCase):
    def test_obvious_high_outlier_flagged(self):
        # 1..9 are tightly clustered; 1000 should trip the Tukey fence.
        nums = [float(i) for i in range(1, 10)] + [1000.0]
        prof = ci.profile_column("v", [str(n) for n in nums])
        self.assertIn(1000.0, prof.outliers)
        self.assertEqual(len(prof.outliers), 1)

    def test_no_outliers_in_uniform_data(self):
        prof = ci.profile_column("v", ["1", "2", "3", "4", "5"])
        self.assertEqual(prof.outliers, [])

    def test_zero_iqr_reports_no_outliers(self):
        # Mostly-identical values collapse p25 == p75, so IQR == 0;
        # find_outliers should treat this as "nothing to flag" rather
        # than dividing by zero or flagging everything.
        nums = [5.0, 5.0, 5.0, 5.0, 100.0]
        outliers = ci.find_outliers(nums, q25=5.0, q75=5.0)
        self.assertEqual(outliers, [])

    def test_single_value_column_has_no_outliers(self):
        prof = ci.profile_column("v", ["42"])
        self.assertEqual(prof.outliers, [])

    def test_json_includes_outlier_count(self):
        header = ["v"]
        data = [[str(n)] for n in list(range(1, 10)) + [1000]]
        profiles = ci.build_profiles(header, data)
        payload = ci.build_json("data.csv", header, data, profiles)
        self.assertEqual(payload["profiles"][0]["outlier_count"], 1)


class RaggedRowTests(unittest.TestCase):
    def test_short_rows_are_padded(self):
        header = ["a", "b", "c"]
        data = [["1", "2"], ["3", "4", "5"]]  # first row is short
        profiles = ci.build_profiles(header, data)
        # column "c" should have one missing value from the short row
        self.assertEqual(profiles[2].missing, 1)


if __name__ == "__main__":
    unittest.main()
