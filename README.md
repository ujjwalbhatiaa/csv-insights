# csv-insights

A tiny, **dependency-free** CSV data profiler in pure Python. Point it at any CSV and get an instant summary — row/column counts, inferred column types, missing values, unique counts, descriptive statistics for every numeric column, and the most-frequent values for text columns.

No `pandas`, no installs, no setup. Just the Python standard library.

## Why
When you get a new dataset, the first thing you want is a quick feel for it: what's in each column, how much is missing, the basic stats, and what the common categories are. `csv-insights` does exactly that in one command.

## Usage
```bash
python csv_insights.py data.csv              # text report
python csv_insights.py data.csv --top 5      # show top 5 values per text column
python csv_insights.py data.csv --json       # machine-readable JSON output
python csv_insights.py data.csv --hist       # terminal histograms (8 bins)
python csv_insights.py data.csv --hist 12    # ...or pick the bin count
```

### Histograms
`--hist` draws an equal-width histogram under every numeric column, right in the terminal (`python csv_insights.py sample.csv --hist 4`):
```text
  age  [integer]
    fill:  75.0%   missing: 1   unique: 3
    min 23.00  max 31.00  mean 27.33  median 28.00  std 3.30
    p25 23.00  p75 31.00
      23.00 – 25.00 | ████████████████████████ 1
      25.00 – 27.00 |  0
      27.00 – 29.00 | ████████████████████████ 1
      29.00 – 31.00 | ████████████████████████ 1
```
Histogram data is included in `--json` output too (a `histogram` array of `{lo, hi, count}` bins per numeric column).

## Example
```text
================================================================
  csv-insights  ·  sample.csv
================================================================
  Rows: 4    Columns: 4
================================================================

  name  [text]
    fill: 100.0%   missing: 0   unique: 4
    top: 'Alice'×1  'Bob'×1  'Cara'×1

  age  [integer]
    fill:  75.0%   missing: 1   unique: 3
    min 23.00  max 31.00  mean 27.33  median 28.00  std 3.30
    p25 23.00  p75 31.00

  city  [text]
    fill: 100.0%   missing: 0   unique: 3
    top: 'Edmonton'×2  'Calgary'×1  'Toronto'×1
```

### JSON output
`--json` emits the full profile as structured JSON, handy for piping into other tools:
```bash
python csv_insights.py data.csv --json | jq '.profiles[] | {name, dtype, missing}'
```

## What it does
- Infers each column's type (`integer`, `float`, `text`, `empty`)
- Reports fill rate, missing count, and unique count per column
- Computes min, max, mean, median, standard deviation, and the 25th/75th percentiles for numeric columns
- Lists the most-frequent values for text/categorical columns (`--top N`)
- Emits a machine-readable JSON summary with `--json`
- Handles ragged rows and UTF-8 BOM gracefully

## Tests
```bash
python -m unittest test_csv_insights -v
```
The test suite uses only the standard-library `unittest` module — no dependencies.

## Tech
Python 3 · standard library only (`csv`, `statistics`, `argparse`, `json`, `collections`, `dataclasses`)

## Roadmap
- [x] Optional JSON output (`--json`)
- [x] Most-frequent values for categorical columns
- [x] Per-column percentiles (p25 / p75)
- [x] Histograms for numeric columns in the terminal (`--hist`)

---
Built by [Ujjwal Bhatia](https://github.com/ujjwalbhatiaa) · BSc Honours Computing Science (AI) @ University of Alberta
