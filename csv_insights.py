#!/usr/bin/env python3
"""
csv-insights — a tiny, dependency-free CSV data profiler.

Point it at any CSV and it prints a clean summary: row/column counts,
inferred column types, missing values, unique counts, descriptive
statistics for numeric columns (min, max, mean, median, std dev), and
the most-frequent values for text columns.

Pure Python standard library — no pandas, no installs.

Usage:
    python csv_insights.py data.csv
    python csv_insights.py data.csv --top 5      # show 5 top values per text column
    python csv_insights.py data.csv --json       # emit machine-readable JSON
    python csv_insights.py data.csv --hist       # terminal histograms for numeric columns
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from collections import Counter
from dataclasses import asdict, dataclass, field


# --------------------------------------------------------------------------- #
# Type inference helpers
# --------------------------------------------------------------------------- #
def _is_int(value: str) -> bool:
    try:
        int(value)
        return True
    except ValueError:
        return False


def _is_float(value: str) -> bool:
    try:
        float(value)
        return True
    except ValueError:
        return False


def infer_type(values: list[str]) -> str:
    """Infer a coarse column type from its non-empty values."""
    non_empty = [v for v in values if v.strip() != ""]
    if not non_empty:
        return "empty"
    if all(_is_int(v) for v in non_empty):
        return "integer"
    if all(_is_float(v) for v in non_empty):
        return "float"
    return "text"


# --------------------------------------------------------------------------- #
# Histogram
# --------------------------------------------------------------------------- #
def build_histogram(nums: list[float], bins: int = 8) -> list[dict]:
    """Bucket numeric values into equal-width bins.

    Returns a list of {"lo": float, "hi": float, "count": int} dicts.
    If every value is identical, a single bin holding all values is returned.
    """
    if not nums or bins < 1:
        return []
    lo, hi = min(nums), max(nums)
    if lo == hi:
        return [{"lo": lo, "hi": hi, "count": len(nums)}]
    width = (hi - lo) / bins
    counts = [0] * bins
    for v in nums:
        # The maximum value lands in the last bin instead of overflowing.
        idx = min(int((v - lo) / width), bins - 1)
        counts[idx] += 1
    return [
        {"lo": lo + i * width, "hi": lo + (i + 1) * width, "count": counts[i]}
        for i in range(bins)
    ]


# --------------------------------------------------------------------------- #
# Column profile
# --------------------------------------------------------------------------- #
@dataclass
class ColumnProfile:
    name: str
    dtype: str = "text"
    total: int = 0
    missing: int = 0
    unique: int = 0
    stats: dict = field(default_factory=dict)
    top_values: list = field(default_factory=list)
    histogram: list = field(default_factory=list)

    @property
    def fill_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return 100.0 * (self.total - self.missing) / self.total


def profile_column(name: str, values: list[str], top: int = 3,
                   bins: int = 0) -> ColumnProfile:
    total = len(values)
    missing = sum(1 for v in values if v.strip() == "")
    non_empty = [v for v in values if v.strip() != ""]
    dtype = infer_type(values)

    prof = ColumnProfile(
        name=name,
        dtype=dtype,
        total=total,
        missing=missing,
        unique=len(set(non_empty)),
    )

    if dtype in ("integer", "float") and non_empty:
        nums = [float(v) for v in non_empty]
        if len(nums) > 1:
            # statistics.quantiles(n=4) returns the three quartile cut points
            # [p25, p50, p75]; we surface the 25th and 75th percentiles.
            q25, _, q75 = statistics.quantiles(nums, n=4)
        else:
            q25 = q75 = nums[0]
        prof.stats = {
            "min": min(nums),
            "max": max(nums),
            "mean": statistics.fmean(nums),
            "median": statistics.median(nums),
            "stdev": statistics.pstdev(nums) if len(nums) > 1 else 0.0,
            "p25": q25,
            "p75": q75,
        }
        if bins > 0:
            prof.histogram = build_histogram(nums, bins=bins)
    elif dtype == "text" and non_empty and top > 0:
        # Most-frequent values for categorical/text columns.
        prof.top_values = [
            {"value": value, "count": count}
            for value, count in Counter(non_empty).most_common(top)
        ]

    return prof


# --------------------------------------------------------------------------- #
# Reading + reporting
# --------------------------------------------------------------------------- #
def read_csv(path: str) -> tuple[list[str], list[list[str]]]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        rows = list(reader)
    if not rows:
        raise ValueError("CSV file is empty.")
    header, *data = rows
    return header, data


def build_profiles(header: list[str], data: list[list[str]],
                   top: int = 3, bins: int = 0) -> list[ColumnProfile]:
    profiles = []
    for i, name in enumerate(header):
        column = [row[i] if i < len(row) else "" for row in data]
        profiles.append(profile_column(name, column, top=top, bins=bins))
    return profiles


def _fmt(n: float) -> str:
    return f"{n:.2f}" if isinstance(n, float) else str(n)


def print_report(path: str, header: list[str], data: list[list[str]],
                 profiles: list[ColumnProfile]) -> None:
    line = "=" * 64
    print(line)
    print(f"  csv-insights  ·  {path}")
    print(line)
    print(f"  Rows: {len(data):,}    Columns: {len(header)}")
    print(line)

    for p in profiles:
        print(f"\n  {p.name}  [{p.dtype}]")
        print(f"    fill: {p.fill_rate:5.1f}%   missing: {p.missing}   unique: {p.unique}")
        if p.stats:
            s = p.stats
            print(f"    min {_fmt(s['min'])}  max {_fmt(s['max'])}  "
                  f"mean {_fmt(s['mean'])}  median {_fmt(s['median'])}  "
                  f"std {_fmt(s['stdev'])}")
            print(f"    p25 {_fmt(s['p25'])}  p75 {_fmt(s['p75'])}")
        if p.histogram:
            max_count = max(b["count"] for b in p.histogram) or 1
            label_w = max(
                len(f"{_fmt(b['lo'])} – {_fmt(b['hi'])}") for b in p.histogram
            )
            for b in p.histogram:
                bar = "█" * round(24 * b["count"] / max_count)
                label = f"{_fmt(b['lo'])} – {_fmt(b['hi'])}".rjust(label_w)
                print(f"      {label} | {bar} {b['count']}")
        if p.top_values:
            top_str = "  ".join(
                f"{tv['value']!r}×{tv['count']}" for tv in p.top_values
            )
            print(f"    top: {top_str}")
    print("\n" + line)


def build_json(path: str, header: list[str], data: list[list[str]],
               profiles: list[ColumnProfile]) -> dict:
    """Assemble a machine-readable summary of the profiled CSV."""
    columns = []
    for p in profiles:
        col = asdict(p)
        col["fill_rate"] = round(p.fill_rate, 2)
        columns.append(col)
    return {
        "file": path,
        "rows": len(data),
        "columns": len(header),
        "profiles": columns,
    }


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Profile a CSV file: types, missing values, and stats."
    )
    parser.add_argument("path", help="Path to the CSV file")
    parser.add_argument(
        "--top", type=int, default=3, metavar="N",
        help="Number of most-frequent values to show per text column (default: 3)",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Emit the profile as JSON instead of a text report",
    )
    parser.add_argument(
        "--hist", nargs="?", type=int, const=8, default=0, metavar="BINS",
        help="Show a terminal histogram for each numeric column "
             "(optionally set the number of bins; default: 8)",
    )
    args = parser.parse_args(argv)

    try:
        header, data = read_csv(args.path)
    except FileNotFoundError:
        print(f"Error: file not found: {args.path}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    profiles = build_profiles(header, data, top=args.top, bins=args.hist)

    if args.json:
        print(json.dumps(build_json(args.path, header, data, profiles), indent=2))
    else:
        print_report(args.path, header, data, profiles)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
