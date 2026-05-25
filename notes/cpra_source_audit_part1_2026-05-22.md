# CPRA source audit — Part 1: structural inventory of the source file

**Generated:** 2026-05-22T14:06:10
**Scope:** read-only structural look at the CPRA source file and the 2018–2022 request document. No comparison to v2; no ingestion-script audit; no permit-tracing.

## Source file metadata

| field | value |
|---|---|
| Path | `~/Library/CloudStorage/GoogleDrive-[redacted-email]/My Drive/Corridors/BP-downloads/BP_Annual Permit Report.xlsx` |
| Size | 2,839,652 bytes (~2.8 MB) |
| Modified | 2026-05-10 11:09:00 |
| File type | Microsoft Excel 2007+ |
| SHA256 | `b7fae82b0c14cf97d330aa4990eb3353348b1b1aaa2e88f30edade18507db52e` |
| Materialized locally | yes (not a Google Drive placeholder) |

## 1. The 2018–2022 request document (context)

`docs/cpra/2026-05-10_request_2018-2022.md` is a follow-up CPRA request **sent 2026-05-10**, status "Submitted, awaiting response". It asks for:

- **Part 1:** Building Permits 2018–2022 — same field set as the prior delivery (the file audited here), plus three additions: parent-permit reference (to reduce sub-permit noise), affordability/BMR designation per permit, and explicit "finalized" alias for Certificate of Occupancy.
- **Part 2:** Planning Records 2018–2022 — a brand-new dataset (not previously requested) drawn from Accela's Planning module: ZP, AUP, UP, PLN, LMSAP, Design Review record types.
- Acceptance of longer response time given expanded scope.
- Expected size for Part 1: probably 25,000–35,000 rows.
- The request explicitly notes about the **previous response** (the file audited here): "the delivered Excel did not include all of these. This request re-asks for those fields" — referring to CO date, applicant/contractor name, and total fees assessed.

Key context from the request doc that is relevant to this audit:

- The previous CPRA was **fulfilled April 20, 2026** and produced this file (`BP_Annual Permit Report.xlsx`), described in the doc as **"14,143 rows, 2023–2025"**.
- The previous request scope was **residential building permits only** — Planning records were not requested. This explains why the file we have contains only B-prefix permits.
- The doc lists fields the previous response **omitted**: CO Date, applicant/contractor name, total fees assessed.

## 2. Workbook structure

| property | value |
|---|---|
| Sheet count | 1 |
| Sheet name | `BP_Annual Permit Report` |
| max_row (sheet) | 14,157 |
| max_col (sheet) | 26 |
| Data rows (after `header=7`) | **14,149** |
| Discrepancy vs the request doc's "14,143 rows" | +6 (explained by 6 duplicate PermitNumbers — see §6) |
| Column count | 26 (with 3 unnamed spacer columns + 1 legitimately-empty Completed Date) |
| Title row | row 3: `BP Annual Permit Report` |
| Date-range row | row 5: `For Post Date: 1/1/2023 to 12/31/2025` |
| Header row | row 8 |
| First data row | row 9 |
| Trailer rows | none (last row is a legitimate permit) |

### Preamble rows 1–7 (verbatim, only non-empty cells)

```
row 1: (all empty)
row 2: (all empty)
row 3: col D = 'BP Annual Permit Report'
row 4: (all empty)
row 5: col E = 'For Post Date: 1/1/2023 to 12/31/2025'
row 6: (all empty)
row 7: (all empty)
```

Note the cutoff phrasing is **"Post Date"** — Accela's term for the date the record was posted/published. This is not necessarily the same as Issuance Date; see §5 on the 4 rows that have Issuance Date past 2025-12-31.

## 3. Full column list

| idx | column | dtype | non_null | uniq | notes |
|---|---|---|---|---|---|
| 0 | PermitNumber | object | 14149/14149 | 14143 | 6 dup numbers (each appearing on 2 rows tied to different parcels) |
| 1 | Submittal Date | datetime64[ns] | 14149/14149 | 1431 | range 2004-11-08 → 2025-12-31 |
| 2 | Issuance Status | object | 13983/14149 | **1** | constant = `'Issued'` (166 nulls) |
| 3 | Unnamed: 3 | float64 | 0/14149 | 0 | **spacer (empty)** |
| 4 | Issuance Date | object | 13983/14149 | 1329 | string-formatted dates; parses cleanly. Range 2016-06-07 → 2026-02-04 |
| 5 | Finaled Status | object | 10777/14149 | **1** | constant = `'Finaled'` (3372 nulls) |
| 6 | Finaled Date | datetime64[ns] | 10071/14149 | 744 | range 2023-01-03 → 2025-12-31 |
| 7 | Completed | object | **4/14149** | 1 | constant = `'Closed Complete'` for the 4 non-null; mostly null |
| 8 | Completed Date | float64 | **0/14149** | 0 | **empty column** (the "CO Date" the request doc says was omitted) |
| 9 | Parcel Number | object | 14148/14149 | 7647 | 1 null |
| 10 | StreetNumber | float64 | 14138/14149 | 2319 | numeric; min=0, max=6621 |
| 11 | StreetName | object | 14138/14149 | 375 | mixed case; e.g., 'SPRUCE' (237), 'GRIZZLY PEAK' (228), 'OXFORD' (199) |
| 12 | Unnamed: 12 | float64 | 0/14149 | 0 | **spacer** |
| 13 | StreetType | object | 13929/14149 | 16 | has case-duplicates: 'St' (6799) vs 'ST' (7); 'Ave' (4308) vs 'AVE' (16) |
| 14 | JobValuation | float64 | 14119/14149 | 2787 | range -$150,000 → $50,000,000; 3 negative, 4050 zero |
| 15 | WorkDescription | object | 14120/14149 | 13281 | free-text |
| 16 | Unnamed: 16 | float64 | 0/14149 | 0 | **spacer** |
| 17 | ADU | object | 14149/14149 | 2 | `'No data available'` (11505) + `'Yes'` (2644) |
| 18 | Detached | object | 778/14149 | 2 | `'No'` (412) + `'Yes'` (366); mostly null |
| 19 | Work Type | object | 13634/14149 | 6 | Alteration / New / Addition/Alteration / Addition / Demolition / Sign |
| 20 | OccType | object | 14149/14149 | 18 | mostly R-3 (11066) and R-2 (2128); 128 `'undefined'`, 3 `'97R3'`, plus self-describing data-quality issues |
| 21 | SubType | object | 14149/14149 | 2 | Residential (13959) / Mixed Use (190) |
| 22 | NumberUnits | float64 | 8731/14149 | 77 | range 0–207 (max matches the 1598 University Ave 207-unit project) |
| 23 | UnitsAdded | float64 | 3010/14149 | 39 | range 0–207 |
| 24 | UnitsRemoved | float64 | 1807/14149 | 31 | range 0–92 |
| 25 | CO Required | object | 9470/14149 | 2 | `'No'` (8659) + `'Yes'` (811); 4679 null |

**Fields the request doc says were omitted (and verified absent here):** applicant/contractor name, total fees assessed, Certificate of Occupancy date (Completed Date is 0/14149 non-null). The request doc's claim is correct.

## 4. Per-column distributions (categorical / small-cardinality)

### Work Type (n=6)

| value | count |
|---|---|
| Alteration | 11591 |
| New | 873 |
| Addition/Alteration | 630 |
| (null) | 515 |
| Addition | 324 |
| Demolition | 169 |
| Sign | 47 |

### OccType (n=18)

| value | count |
|---|---|
| `R-3 Residential: Dwellings (1 or 2 Units), Townhomes, Congregate Living` | 11066 |
| `R-2 Residential: Permanent, Multi-Unit (3+ Units)` | 2128 |
| `Not Applicable (new)` | 383 |
| `U Private Garages, Carports, Sheds, Agricultural, Tanks, Accessory` | 278 |
| `undefined` | 128 |
| `R-3.1 Residential: Licensed Residential Care Facility for 6 or fewer Clients` | 36 |
| `R-1 Residential: Transient/Hotels/Motels` | 32 |
| `R-2.1 Residential: Supervised Residential Care Services` | 28 |
| `B Business` | 21 |
| `A-2 Assembly: Food or Drink Consumption` | 11 |
| `R-2` | 10 |
| `R-3` | 8 |
| `A-3 Assembly: Worship, Recreation, Etc` | 5 |
| `F-1 Factory Industrial: Moderate-hazard` | 5 |
| `R-4 Residential: Supervised Assisted Living and Residential Care for 7+ Ambulatory and < 7 Nonambtry` | 5 |
| `97R3` | 3 |
| `E Educational (K-12) for 7+ Students or Day Care for 7+ Children older than 2.5 Years` | 1 |
| `I-1 Not used, see R-2.1` | 1 |

Data-quality observations: `'undefined'` (128), `'97R3'` (3, likely a code typo), bare `'R-2'` (10) and `'R-3'` (8) without the full description, and the self-described `'I-1 Not used, see R-2.1'` (1, a system note that leaked into the data).

### SubType (n=2)

| value | count |
|---|---|
| Residential | 13959 |
| Mixed Use | 190 |

### ADU (n=2)

| value | count |
|---|---|
| No data available | 11505 |
| Yes | 2644 |

The `'No data available'` is Accela's placeholder when the ADU field isn't applicable to that permit type — it means "this is not an ADU permit", not "missing". 2,644 ADU permits issued in 2023–2025 by this measure.

### Detached (n=2 non-null)

| value | count |
|---|---|
| (null) | 13371 |
| No | 412 |
| Yes | 366 |

### CO Required (n=2 non-null)

| value | count |
|---|---|
| No | 8659 |
| (null) | 4679 |
| Yes | 811 |

### StreetType (n=16)

| value | count |
|---|---|
| St | 6799 |
| Ave | 4308 |
| Rd | 993 |
| Way | 864 |
| Dr | 310 |
| Blvd | 294 |
| (null) | 220 |
| Pl | 108 |
| Ct | 83 |
| Ln | 69 |
| Ter | 36 |
| Cir | 29 |
| AVE | 16 |
| ST | 7 |
| Cres | 7 |
| Path | 5 |
| Walk | 1 |

Case-duplicates: `St`/`ST`, `Ave`/`AVE` are the same designator with different casing. A normalize-to-lowercase pass would collapse 16 → 14.

### Constant-value columns

- `Issuance Status` = `'Issued'` (only value; 166 nulls)
- `Finaled Status` = `'Finaled'` (only value; 3372 nulls)
- `Completed` = `'Closed Complete'` (only 4 non-null rows)

These act as flags: a row's `Finaled Status` is either `'Finaled'` or null; same for `Issuance Status`.

## 5. Numeric and date column stats

| column | non_null | min | max | mean | median |
|---|---|---|---|---|---|
| StreetNumber | 14138 | 0 | 6621 | 1614.5 | 1598 |
| JobValuation | 14119 | -150,000 | 50,000,000 | 330,774 | 9,000 |
| NumberUnits | 8731 | 0 | 207 | 4.77 | 1 |
| UnitsAdded | 3010 | 0 | 207 | 7.62 | 0 |
| UnitsRemoved | 1807 | 0 | 92 | 1.66 | 0 |

Date columns:

| column | non_null | min | max |
|---|---|---|---|
| Submittal Date | 14149 | 2004-11-08 | 2025-12-31 |
| Issuance Date (parsed) | 13983 | 2016-06-07 | **2026-02-04** |
| Finaled Date | 10071 | 2023-01-03 | 2025-12-31 |

The Issuance Date column has 4 rows past 2025-12-31:
  - 4 rows with Issuance Date in 2026
  - The preamble says "For Post Date: 1/1/2023 to 12/31/2025" — so Accela filtered by Post Date, not by Issuance Date. These 4 are within scope by Post Date but issued slightly past the apparent cutoff.

## 6. Permit-number distribution and year coverage

### Permit-number prefix (only one)

| prefix | count |
|---|---|
| `B` | 14149 |

100% B-permits. The CPRA was scoped to Building Permits only — no ZP/PLN/LMSAP. The follow-up 2018–2022 request explicitly adds Planning records as Part 2.

### Year extracted from the permit number

| permit-number year | count |
|---|---|
| 2004 | 1 |
| 2005 | 1 |
| 2006 | 1 |
| 2010 | 1 |
| 2011 | 1 |
| 2013 | 2 |
| 2014 | 13 |
| 2015 | 3 |
| 2016 | 11 |
| 2017 | 33 |
| 2018 | 38 |
| 2019 | 131 |
| 2020 | 171 |
| 2021 | 572 |
| 2022 | 1747 |
| 2023 | 4124 |
| 2024 | 3889 |
| 2025 | 3410 |

The permit-number year reflects when the permit was *originally filed*, not when it was issued. Reflects a long tail of older permits (back to B2004) that got issued or finaled inside the 2023–2025 Post Date window.

### Year per Issuance Date

| issued year | count |
|---|---|
| 2016.0 | 3 |
| 2017.0 | 9 |
| 2018.0 | 18 |
| 2019.0 | 37 |
| 2020.0 | 55 |
| 2021.0 | 208 |
| 2022.0 | 1080 |
| 2023.0 | 4230 |
| 2024.0 | 4145 |
| 2025.0 | 4194 |
| 2026.0 | 4 |
| nan | 166 |

### Year per Submittal Date

| submittal year | count |
|---|---|
| 2004 | 1 |
| 2005 | 1 |
| 2006 | 1 |
| 2010 | 1 |
| 2011 | 1 |
| 2013 | 1 |
| 2014 | 2 |
| 2015 | 1 |
| 2016 | 11 |
| 2017 | 20 |
| 2018 | 27 |
| 2019 | 86 |
| 2020 | 109 |
| 2021 | 353 |
| 2022 | 1508 |
| 2023 | 4218 |
| 2024 | 4116 |
| 2025 | 3692 |

### Year per Finaled Date

| finaled year | count |
|---|---|
| 2023.0 | 3004 |
| 2024.0 | 3378 |
| 2025.0 | 3689 |
| nan | 4078 |

## 7. Anomalies

### Duplicate PermitNumbers — 6 distinct numbers, 12 rows total

Each duplicate is the same permit appearing on **two different parcels** — i.e., one permit covers multiple parcels and Accela outputs one row per (permit × parcel). Not true duplicates.

| PermitNumber | rows | parcels |
|---|---|---|
| `B2025-05472` | 2 | 064 423602100, 064 423602400 |
| `B2025-01664-REV01` | 2 | 060 247503500, 060 247503600 |
| `B2025-01664` | 2 | 060 247503500, 060 247503600 |
| `B2023-04532` | 2 | 053 161603400, 059 229301400 |
| `B2022-03215-REV01` | 2 | 063 296802600, 063 314011800 |
| `B2022-03215` | 2 | 063 296802600, 063 314011800 |

Ingestion concern: a naive `INSERT OR IGNORE ON permit_number` would import one of the two rows and lose the second parcel link. Worth verifying in Part 2 (ingestion-script audit) that this case is handled correctly.

### Future-dated rows

- None of the three date columns has dates past today.
- 4 rows have Issuance Date past the preamble's stated cutoff of 2025-12-31 (all in early 2026).
- 0 Submittal Dates and 0 Finaled Dates past 2025-12-31.

### Negative valuations — 3 rows

- min JobValuation = -$150,000. 3 negative-valuation rows total. Likely demolition or removal credits.

### Zero valuations — 4,050 rows (29%)

- Common for sub-permits and electrical/plumbing/mechanical changeouts where the parent permit holds the value.

### Rows with NULL PermitNumber

- **None** (0 rows). The data is reliable on this primary key.

### All-null columns (4)

- `Unnamed: 3`, `Unnamed: 12`, `Unnamed: 16` — spacer/divider columns from the Accela export. No data ever.
- `Completed Date` — legitimately empty. The request doc explicitly notes this field was omitted in the previous response; the 2018–2022 request re-asks for it.

### Constant-value columns

- `Issuance Status` = `'Issued'` (when not null). Functions as a flag, not a discriminator.
- `Finaled Status` = `'Finaled'` (when not null). Same.
- `Completed` = `'Closed Complete'` (when not null; only 4 rows).

## Bottom-line summary

- **Source:** `BP_Annual Permit Report.xlsx`, 2.8 MB, modified 2026-05-10, SHA256 `b7fae82b…`. One sheet: `BP_Annual Permit Report`.
- **Data rows:** **14,149** (+6 vs the request doc's "14,143" — explained by 6 multi-parcel permits emitted as 2 rows each).
- **Columns:** 26 total (22 data-bearing + 3 unnamed spacers + 1 empty Completed Date).
- **Permit-number column:** `PermitNumber` — 100% B-prefix (14,149/14,149); 0 nulls; 14,143 distinct values.
- **Permit prefix distribution:** B=14149 (the only prefix in this file).
- **Year range covered:**
  - by permit number: 2004–2025 (median permit year 2023; mostly 2022–2025)
  - by Issuance Date: 2016-06-07 → 2026-02-04 (4 rows past the stated cutoff)
  - by Submittal Date: 2004-11-08 → 2025-12-31
  - by Finaled Date: 2023-01-03 → 2025-12-31 (only 2023+ finalizations)
- **Match against the 2018–2022 request:** the file we have is the **previous (2023–2025) CPRA batch**, not the 2018–2022 batch. The 2018–2022 file would be a separate forthcoming delivery. This audit covers the 2023–2025 file only; the 2018–2022 batch is still pending per the request doc ("Status: Submitted, awaiting response").
