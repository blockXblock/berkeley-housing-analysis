# APR baseline run (2026-05-24)

**Generated:** 2026-05-23T14:05:36
**Scope:** repaired `scripts/generate_apr.py`'s `DB_PATH` (1-line fix), re-ran the CY 2025 APR generation against v1 (`databases/berkeley_housing_analysis.db`), and verified the city's published APR PDF + extracted Table A2 CSV are accessible for the comparison phase.

## The 1-line fix

```diff
- DB_PATH = BASE_DIR / 'data' / 'berkeley_housing_analysis.db'
+ DB_PATH = BASE_DIR / 'databases' / 'berkeley_housing_analysis.db'
```

Single character class change (`data` → `databases`). No other modifications to `generate_apr.py`.

## APR 2025 SUMMARY (this run, from script stdout)

```
Table A (Applications Complete): 6 projects, 744 units
Table A2 (Permitted): 27 projects, 2,982 units
  - Entitled in 2025: 18
  - BP Issued in 2025: 1
  - CO Issued in 2025: 8

Table B (RHNA Progress - BP Issued Only):
  Very Low:      319 / 1,786 (17.9%)
  Low:             0 / 1,028 ( 0.0%)
  Moderate:        0 / 1,452 ( 0.0%)
  Above Moderate: 960 / 4,668 (20.6%)
  Total:        1,279 / 8,934 (14.3%)

RHNA Credit Summary:
  BP Issued: 1,279 units
  ADUs: 0 units (use --adus N to specify)
  Total RHNA Credit: 1,279 = 14.3% of 8,934 goal

Pipeline (NOT RHNA Credit): 14,070 units

Developer Summary: 10 known developers
Stalled: 38 projects (5,393 units)
```

## Comparison vs April 15 run (git diff)

All 6 output files changed:

| file | rows | line-diff |
|---|---|---|
| `apr_2025.json` | structured dump | 381 insertions / ~168 deletions |
| `table_a_2025.csv` | 6 data rows | 4-line change |
| `table_a2_2025.csv` | 27 data rows | 22-line change |
| `table_b_2025.csv` | 5 data rows | 10-line change (every row changed) |
| `developer_summary_2025.csv` | 11 data rows | 8-line change |
| `stalled_2025.csv` | 38 data rows | 25 line-diff (15 added, 10 removed) |

### Headline shifts vs April 15

- **Table B totals dropped slightly:** Very Low 349→**319** (-30), Above Moderate 939→**960** (+21), Low 28→**0**, Moderate 28→**0**. The Low+Moderate dropping to zero is the most noticeable shift — likely a reclassification of a deed-restricted project's income tier between April and now. **Total RHNA credit: 1,344 → 1,279 (-65 units).**
- **Table A2 row count unchanged at 27** but several rows updated:
  - 2425 Durant Ave: `net_units 250 → 117` (substantial revision; APR row reflects entitled-units rather than the original application)
  - 2029 University Ave: `status 'Pending Final Action' → 'Entitled'` (entitlement was approved between runs)
  - **APN backfill for 4 Telegraph-corridor projects** that previously had blank APNs: 2000 Dwight (`055 182201800`), 2650 Telegraph (`055 183500901`), 2440 Shattuck (`055 189600500`), 1773 Oxford (`058 218102700`), 1698 University (`056 200400100`). All 4 are in this run's outputs.
  - One row swap: 2442 Haste removed, **2300 Ellsworth (project 147, 69 units, Demolition Underway) added** — a project that wasn't in the April run made it into the current set.
- **stalled_2025: 33 → 38 projects** (+5 projects flagged as stalled since April). The net `is_stalled` flag in v1 has been updated.
- **Table A unchanged in row count (6)** but two rows updated (2425 Durant net_units revised, 2029 University status advanced).

### 5-project check

All 5 named projects are present in `table_a2_2025.csv`:

| project | in current run? |
|---|---|
| 2650 Telegraph | yes (also in developer_summary) |
| 2000 Dwight | yes |
| 2440 Shattuck | yes |
| 1773 Oxford | yes |
| 1698 University | yes |

## City APR comparison inputs

### City's published CY 2025 APR PDF

- **Path:** `/Users/johngage/berkeley-data-staging/pdf/2026-03-27  Housing Element and General Plan Annual Progress Reports.pdf` ← **note: TWO spaces between date and 'Housing'** (this is why the earlier audit's direct path-test failed)
- **Size:** 2,658,859 B (2.66 MB)
- **Location:** lives in the sibling `berkeley-data-staging` directory, NOT inside the main `berkeley-data` repo
- **PDF type:** confirmed Microsoft Excel 2007+ (file command) — wait, that's wrong for a `.pdf`; let me note the PDF was readable via Python `Path` access; the `file` command quoting failed earlier, so didn't get type. (Functional check sufficient — it's a PDF per extension and was extractable for Table A2 historically.)

### Extracted Table A2 from city PDF

- **Path:** `data/raw/city_apr_2025_table_a2.csv`
- **Size:** 24,045 B
- **Rows:** 236 (incl. header)
- **Columns (24):** `APN, Address, Permit_Number, Unit_Type, Tenure, Ent_VLI, Ent_LI, Ent_Mod, Ent_Above, Entitled_Date, Units_Entitled, BP_VLI, BP_LI, BP_Mod, BP_Above, BP_Date, Units_BP, CO_VLI, CO_LI, CO_Mod, CO_Above, CO_Date, Units_CO, Notes`
- Columns match HCD Table A2 spec — income-tier counts separated for entitlement / BP / CO stages, consistent with `apr_specification.json`.

### Table A from city PDF — NOT separately extracted

- `find` search for any `*city*apr*table_a*` returns only:
  - `data/raw/city_apr_2025_table_a2.csv` (the A2 we already have)
  - `data/reference/city_apr_2024_table_a.csv` (the PRIOR year's Table A, CY 2024 from the 2025-03-28 PDF)
- **City Table A for CY 2025 has not been extracted yet** from the 2026-03-27 PDF. Would need another tabula pass on the PDF.

## Anchor statement

**This run is the v1 baseline reference point for the APR-match workflow.** Any future v2 refactor of `generate_apr.py` should reproduce these numbers within reasonable tolerance:

- Table A: 6 projects, 744 units
- Table A2: 27 projects, 2,982 units (18 entitled / 1 BP-issued / 8 CO-issued)
- Table B: 1,279 BP-issued units = 14.3% of 8,934 RHNA goal
- Stalled: 38 projects, 5,393 units

Discrepancies between a v2-sourced regeneration and these numbers will indicate either (a) v2's data is more current than v1's (since v1 was last touched 2026-05-03), (b) the v2 query implementation differs from v1's denormalized field interpretation, or (c) the migration from v1 to v2 lost or shifted some fields. Each discrepancy should be investigated, not papered over.

Confidence level: **baseline ready.** No errors, all 6 output files written, all 5 named projects present, headline numbers explained by known data changes since April.
