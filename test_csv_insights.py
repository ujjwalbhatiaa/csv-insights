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


class DuplicateRowTests(unittest.TestCase):
    def test_no_duplicates_in_unique_data(self):
        data = [["1", "a"], ["2", "b"], ["3", "c"]]
        result = ci.find_duplicate_rows(data)
        self.assertEqual(result["duplicate_row_count"], 0)
        self.assertEqual(result["duplicate_groups"], 0)
        self.assertEqual(result["first_duplicate_indices"], [])

    def test_single_repeated_row_counted_once_per_extra_occurrence(self):
        # Row ["1", "a"] appears 3 times total -> 2 extra occurrences.
        data = [["1", "a"], ["2", "b"], ["1", "a"], ["1", "a"]]
        result = ci.find_duplicate_rows(data)
        self.assertEqual(result["duplicate_row_count"], 2)
        self.assertEqual(result["duplicate_groups"], 1)
        self.assertEqual(result["first_duplicate_indices"], [2, 3])

    def test_multiple_distinct_duplicate_groups(self):
        data = [["1", "a"], ["1", "a"], ["2", "b"], ["2", "b"], ["3", "c"]]
        result = ci.find_duplicate_rows(data)
        self.assertEqual(result["duplicate_row_count"], 2)
        self.assertEqual(result["duplicate_groups"], 2)

    def test_first_duplicate_indices_capped_at_five(self):
        # 7 identical rows -> 6 duplicate occurrences, but the index list
        # should be capped at 5 entries for readability.
        data = [["x"]] * 7
        result = ci.find_duplicate_rows(data)
        self.assertEqual(result["duplicate_row_count"], 6)
        self.assertEqual(len(result["first_duplicate_indices"]), 5)

    def test_json_output_includes_duplicates_summary(self):
        header = ["a"]
        data = [["1"], ["1"], ["2"]]
        profiles = ci.build_profiles(header, data)
        payload = ci.build_json("data.csv", header, data, profiles)
        self.assertIn("duplicates", payload)
        self.assertEqual(payload["duplicates"]["duplicate_row_count"], 1)


class CorrelationTests(unittest.TestCase):
    def test_perfect_positive_correlation(self):
        x = [1.0, 2.0, 3.0, 4.0]
        y = [2.0, 4.0, 6.0, 8.0]
        self.assertAlmostEqual(ci.pearson_correlation(x, y), 1.0)

    def test_perfect_negative_correlation(self):
        x = [1.0, 2.0, 3.0, 4.0]
        y = [8.0, 6.0, 4.0, 2.0]
        self.assertAlmostEqual(ci.pearson_correlation(x, y), -1.0)

    def test_constant_column_returns_none(self):
        # Zero variance means correlation is undefined, not zero.
        x = [5.0, 5.0, 5.0]
        y = [1.0, 2.0, 3.0]
        self.assertIsNone(ci.pearson_correlation(x, y))

    def test_too_few_points_returns_none(self):
        self.assertIsNone(ci.pearson_correlation([1.0], [1.0]))

    def test_mismatched_lengths_return_none(self):
        self.assertIsNone(ci.pearson_correlation([1.0, 2.0], [1.0]))

    def test_build_correlations_pairs_numeric_columns_only(self):
        header = ["a", "b", "city"]
        data = [
            ["1", "2", "X"],
            ["2", "4", "Y"],
            ["3", "6", "Z"],
            ["4", "8", "X"],
        ]
        profiles = ci.build_profiles(header, data)
        corrs = ci.build_correlations(header, data, profiles)
        # Only one numeric pair exists (a, b); the text column is excluded.
        self.assertEqual(len(corrs), 1)
        self.assertEqual({corrs[0]["a"], corrs[0]["b"]}, {"a", "b"})
        self.assertAlmostEqual(corrs[0]["r"], 1.0)

    def test_build_correlations_sorted_by_strength(self):
        header = ["a", "b", "c"]
        data = [
            ["1", "2", "9"],
            ["2", "4", "1"],
            ["3", "5", "8"],
            ["4", "9", "2"],
        ]
        profiles = ci.build_profiles(header, data)
        corrs = ci.build_correlations(header, data, profiles)
        self.assertEqual(len(corrs), 3)  # 3 numeric columns -> 3 pairs
        abs_rs = [abs(c["r"]) for c in corrs]
        self.assertEqual(abs_rs, sorted(abs_rs, reverse=True))

    def test_build_correlations_skips_pairwise_missing_values(self):
        header = ["a", "b"]
        data = [["1", "2"], ["2", ""], ["3", "6"], ["4", "8"]]
        profiles = ci.build_profiles(header, data)
        corrs = ci.build_correlations(header, data, profiles)
        # The row with a missing "b" value is dropped only for this pair;
        # the remaining 3 rows are still a perfect line.
        self.assertEqual(len(corrs), 1)
        self.assertAlmostEqual(corrs[0]["r"], 1.0)

    def test_json_includes_correlations(self):
        header = ["a", "b"]
        data = [["1", "2"], ["2", "4"], ["3", "6"]]
        profiles = ci.build_profiles(header, data)
        payload = ci.build_json("data.csv", header, data, profiles)
        self.assertIn("correlations", payload)
        self.assertEqual(len(payload["correlations"]), 1)


if __name__ == "__main__":
    unittest.main()
