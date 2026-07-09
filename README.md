# csv-insights

A tiny, dependency-free CSV data profiler in pure Python. Point it at any CSV and get an instant summary — row/column counts, inferred column types, missing values, unique counts, descriptive statistics for every numeric column, flagged outliers, pairwise correlation between numeric columns, and the most-frequent values for text columns.

No pandas, no installs, no setup. Just the Python standard library.

## Why

When you get a new dataset, the first thing you want is a quick feel for it: what's in each column, how much is missing, the basic stats, whether anything looks off, which numeric columns move together, and what the common categories are. csv-insights does exactly that in one command.

## Usage

```
python csv_insights.py data.csv            # text report
python csv_insights.py data.csv --top 5     # show top 5 values per text column
python csv_insights.py data.csv --json      # machine-readable JSON output
python csv_insights.py data.csv --hist      # terminal histograms (8 bins)
python csv_insights.py data.csv --hist 12   # ...or pick the bin count
```

## Outlier detection

Every numeric column is automatically checked against the classic Tukey IQR fences — the same rule box-plot whiskers use. A value is flagged if it falls below `p25 - 1.5*IQR` or above `p75 + 1.5*IQR`:

```
age [integer]
  fill: 100.0%   missing: 0   unique: 10
  min 1.00  max 1000.00  mean 104.50  median 5.50  std 298.85
  p25 3.25  p75 7.75
  outliers: 1 [1000.00]
```

No flags, no extra flags — just the values, so you can decide what (if anything) to do about them. Outliers are also included in `--json` output as an `outliers` array plus an `outlier_count` per column.

## Correlations

Every run also computes the pairwise Pearson correlation between every pair of numeric columns, using only the rows where both columns have a value (pairwise-complete). The strongest relationships print first:

```
================================================================
 Correlations (numeric columns, strongest first)
  age <-> height  r = +0.96
================================================================
```

Pairs where `|r| >= 0.5` print by default; if nothing reaches that bar, the strongest few pairs print anyway so the section is never silently empty. A constant column (zero variance) has an undefined correlation and is correctly omitted rather than reported as a fake 0. The full pairwise matrix is included in `--json` output under a top-level `correlations` array of `{a, b, r}` objects.

## Histograms

`--hist` draws an equal-width histogram under every numeric column, right in the terminal (`python csv_insights.py sample.csv --hist 4`):

```
age [integer]
  fill: 75.0%   missing: 1   unique: 3
  min 23.00 max 31.00 mean 27.33 median 28.00 std 3.30
  p25 23.00 p75 31.00
  23.00 – 25.00 | ████████████████████████ 1
  25.00 – 27.00 | 0
  27.00 – 29.00 | ████████████████████████ 1
  29.00 – 31.00 | ████████████████████████ 1
```

Histogram data is included in `--json` output too (a `histogram` array of `{lo, hi, count}` bins per numeric column).

## Duplicate detection

Every run also checks for exact duplicate rows (rows that are byte-for-byte identical) and reports how many extra copies exist and how many distinct rows are repeated:

```
Rows: 4  Columns: 4
Duplicate rows: 1 (across 1 repeated value)
```

Duplicate info is included in `--json` output too, under a top-level `duplicates` key (`duplicate_row_count`, `duplicate_groups`, `first_duplicate_indices`).

## Example

```
========================================================================
csv-insights · sample.csv
========================================================================
Rows: 4  Columns: 4
========================================================================

name [text]
  fill: 100.0%   missing: 0   unique: 4
  top: 'Alice'×1 'Bob'×1 'Cara'×1

age [integer]
  fill: 75.0%   missing: 1   unique: 3
  min 23.00 max 31.00 mean 27.33 median 28.00 std 3.30
  p25 23.00 p75 31.00

city [text]
  fill: 100.0%   missing: 0   unique: 3
  top: 'Edmonton'×2 'Calgary'×1 'Toronto'×1
```

## JSON output

`--json` emits the full profile as structured JSON, handy for piping into other tools:

```
python csv_insights.py data.csv --json | jq '.profiles[] | {name, dtype, missing, outlier_count}'
```

## What it does

- Infers each column's type (integer, float, text, empty)
- Reports fill rate, missing count, and unique count per column
- Computes min, max, mean, median, standard deviation, and the 25th/75th percentiles for numeric columns
- Flags outliers in numeric columns using Tukey's IQR fences
- Computes pairwise Pearson correlation between every pair of numeric columns (pairwise-complete, undefined pairs omitted)
- Lists the most-frequent values for text/categorical columns (`--top N`)
- Detects exact duplicate rows and reports how many extra copies to remove
- Emits a machine-readable JSON summary with `--json`
- Handles ragged rows and UTF-8 BOM gracefully

## Tests

```
python -m unittest test_csv_insights -v
```

The test suite uses only the standard-library `unittest` module — no dependencies.

## Tech

Python 3 · standard library only (`csv`, `statistics`, `itertools`, `argparse`, `json`, `collections`, `dataclasses`)

## Roadmap

- [x] Optional JSON output (`--json`)
- [x] Most-frequent values for categorical columns
- [x] Per-column percentiles (p25 / p75)
- [x] Histograms for numeric columns in the terminal (`--hist`)
- [x] Outlier detection for numeric columns (Tukey IQR fences)
- [x] Exact duplicate-row detection
- [x] Pairwise correlation between numeric columns

---

Built by Ujjwal Bhatia · BSc Honours Computing Science (AI) @ University of Alberta
