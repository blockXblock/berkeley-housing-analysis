# Berkeley CPRA Building Permit fulfillment files

This directory contains the two XLSX files Berkeley released to satisfy two California Public Records Act (CPRA) requests for the city's internal "BP Annual Permit Report" extract. Together they cover Berkeley building permit activity finaled from 2018 through 2025.

## Files

| file | size | rows | fulfillment date | fulfillment channel |
|---|---|---|---|---|
| `BP_Annual Permit Report-2018-2022.xlsx` | 3.5 MB | 18,053 data rows | 2026-05-20 | NextRequest 26-1368 |
| `BP_Annual Permit Report-2023-2025.xlsx` | 2.7 MB | 14,149 data rows | ~2026-04-20 (earlier fulfillment) | (see `notes/cpra_source_inventory_2026-05-22.md`) |

**Joint coverage:** 32,202 total rows; **30,764 unique PermitNumbers**; **1,430 overlapping permits** (permits with Finaled events in both windows, typically issued in one window and finaled in another).

## File-naming note

Berkeley's original fulfillments were both named `BP_Annual Permit Report.xlsx`. The date-range suffixes (`-2018-2022`, `-2023-2025`) were added locally to disambiguate. If you need to verify against the original source, the Google Drive copy at `~/Library/CloudStorage/GoogleDrive-[redacted-email]/My Drive/Corridors/BP-downloads/` carries the canonical (suffixed) name.

## Schema (identical across both files)

Both XLSXs share the same workbook shape:

- Single sheet: `'BP_Annual Permit Report'`
- 6 banner rows + 1 blank + **header row at row 8**; data rows begin at row 9
- 26 columns total

### Columns

| col | header | type | notes |
|---|---|---|---|
| 0 | `PermitNumber` | str | primary key (some duplicates for -REV rows) |
| 1 | `Submittal Date` | datetime | extends back to ~2003-2004 in both files |
| 2 | `Issuance Status` | str | single value: `Issued` |
| 3 | _(spacer)_ | — | |
| 4 | `Issuance Date` | str (MM/DD/YYYY) | stored as text |
| 5 | `Finaled Status` | str | single value: `Finaled` |
| 6 | `Finaled Date` | datetime | **the column the file is scoped by** |
| 7 | `Completed` | str | mostly blank |
| 8 | `Completed Date` | str/datetime | very sparse |
| 9 | `Parcel Number` | str | APN, format `055 183700100` (matches v2 APN format) |
| 10 | `StreetNumber` | int | |
| 11 | `StreetName` | str | |
| 12 | _(spacer)_ | — | |
| 13 | `StreetType` | str | St, Ave, Rd, Way, ... |
| 14 | `JobValuation` | str (numeric) | |
| 15 | `WorkDescription` | str | rich description; matches the description text the CO derivation rule operates on |
| 16 | _(spacer)_ | — | |
| 17 | `ADU` | str | "Yes" / "No" / "No data available" |
| 18 | `Detached` | str | "Yes" / "No" (sparse) |
| 19 | `Work Type` | str | 6 values: Alteration, Addition/Alteration, New, Addition, Demolition, Sign |
| 20 | `OccType` | str | granular occupancy type (R-3, R-2, B, U, A-2, etc.) |
| 21 | `SubType` | str | 2 values: Residential, Mixed Use |
| 22 | `NumberUnits` | str (numeric) | |
| 23 | `UnitsAdded` | str (numeric) | |
| 24 | `UnitsRemoved` | str (numeric) | |
| 25 | `CO Required` | str | "Yes" / blank |

## Critical detail — date scoping

**These files are scoped by `Finaled Date`, NOT by `Submittal Date`.**

The 2018-2022 file's title banner reads `For Post Date: 1/1/2018 to 12/...`. The `Finaled Date` column ranges 2018-01-02 → 2022-12-30 in that file, and 2023-01-03 → 2025-12-31 in the other file. The `Submittal Date` column extends back to 2003 (2018-22 file) or 2004 (2023-25 file) — meaning a permit filed in 2014 that finaled in 2025 appears in the 2023-2025 file, not in 2018-2022.

**Implication:** the prior assumption that pre-2018 BP filings were "out of window" was wrong. They are captured here if they finaled later. The 2026-05-25 ingest-gap diagnostic (see `notes/` from that date) initially classified 3 missing-from-v2 cases as "missed by scrape window"; all 3 are actually present in these CPRA files.

## Distribution highlights (joint across both files)

- **Work Type "New" = 1,773 permits** (873 in 2023-25 + 900 in 2018-22) — these are the housing-pipeline-relevant new-construction permits
- **Alteration dominates** (~26K of ~32K rows) — most permits are tenant improvement / remodel
- **OccType:** R-3 (1-2 unit dwellings, often ADUs) ~25,500; R-2 (3+ unit multifamily) ~4,800
- **SubType:** Residential ~31,600; Mixed Use ~545

## Why these files matter

These XLSXs are the **authoritative source of Berkeley building permit history** for the housing pipeline. Compared to the existing `databases/berkeley_housing_v2.db.permits` table:

1. **Coverage is far broader** — 30,764 unique permits vs. v2's 244. v2 was scoped to project-linked permits matching specific addresses; CPRA delivers Berkeley's full permit registry over the 8-year window.

2. **Schema is richer** — CPRA includes `ADU`, `Work Type`, granular `OccType`, `SubType`, `NumberUnits`, `UnitsAdded`, `UnitsRemoved`, `CO Required`. v2 lacks all of these directly.

3. **Date completeness is better** — `Submittal Date` is universally populated (vs. v2 where most B-permits have NULL `filed_date`).

4. **Classification is correct** — CPRA's `Work Type='New'` correctly identifies new-construction permits that v2 occasionally misclassifies as `'Demolition Permit'` (per the 2026-05-25 audit, ~28% of v2's Demolition Permit rows are mislabeled).

5. **All 8 currently-verified rule-test permits are present** — the 2026-05-25 inventory presence check found 9/9 verified permits in CPRA (the 9th, 1698 University B2014-05752 from 2014, surfaces in 2023-2025 because the file is finaled-date-scoped).

These files are the planned foundation for the D5 (CPRA-first) APR generation workstream. They **supersede `v2.permits` as the authoritative source for housing pipeline analysis**, with v2 continuing to serve as the project-level normalization layer (one project ↔ many permits).

## Verification cross-references

- Schema probe transcript: chat session 2026-05-26
- Prior CPRA source inventory: `notes/cpra_source_inventory_2026-05-22.md`
- 2018-2025 ingest-gap diagnostic: `notes/2026-05-25_apr_workflow_audit.md` (if present) + this session's chat
- CO derivation rule that these files will feed: `notes/2026-05-25_co_derivation_rule_v2.md`

## What this directory is NOT

- Not a database — these are source files. Any database ingest goes elsewhere (planned: a CPRA-sourced table in v2 or a fresh v3 schema for the D5 work).
- Not redacted or summarized — full row-level data as Berkeley released it.
- Not authoritative on Certificate of Occupancy — CPRA reports `Finaled Date`, which is not the same as a Certificate of Occupancy date (Berkeley does not issue traditional COs; see `notes/2026-05-24_apr_workflow_audit.md` §4 for the CO derivation rule that bridges this gap).
