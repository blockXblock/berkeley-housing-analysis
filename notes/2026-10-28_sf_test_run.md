# San Francisco test run of the curriculum chain (2026-10-28)

John, 2026-10-27: "after you fix these gaps, think about a test run bringing up Oakland or San Francisco." 2026-10-28:
"start the San Francisco run." Read-only; everything in `scratch/2026-10-28/sf/` (script `sf_run.py`, inputs `raw/`
pinned in `raw/SHA256SUMS`, outputs `out/`: `changes.csv`, `by_year.csv`, `residuals_C.csv`).

## Inputs (all public, no CPRA)
| Source | What | Rows | SHA-256 |
|---|---|---|---|
| DataSF `i98e-djp9` (data.sf.gov) | building permits issued or completed 2018-2025 | 239,340 rows, 219,481 permits | `33a57d48…` |
| DataSF `j67f-aayr` | DBI "Dwelling Unit Completion Counts by Building Permit" (TCOs, CFCs) | 2,559 | `4b651939…` |
| HCD CKAN `fe505d9b` | SF APR Table A2, JURIS_NAME = SAN FRANCISCO, 2018-2025 (the answer key, never an input) | 5,899 | per-year files |

## Result: completed units, CO years 2018-2025
| Version | Ours | SF's APR | Diff | Buildings agreeing exactly (units and year) |
|---|---|---|---|---|
| A: the notebooks' logic, permit `completed_date` | 24,213 | 29,685 | −18.4% | 1,718 |
| B: DBI certificates only | 23,635 | 29,685 | −20.4% | 1,867 |
| **C: certificates, else permit `completed_date`** | **26,658** | **29,685** | **−10.2%** | **2,017** |

Joined at building level by address, then APN, then permit number (SF's APR puts the DBI permit number in
JURS_TRACKING_ID on 5,227 of 5,899 rows). Under C: 2,186 buildings in both; 68 only in the APR (2,097 u); 128 only ours (1,510 u).

## What explains the rest (C)
- **The APR counts units that have no DBI permit.** 198 McAllister "Academe" (UC Law SF student housing, 657 u, the
  state-agency exemption Berkeley applies to UC; SF counts it) and Mission Rock on Port land (1011 3rd St 283 u, 1070
  Bridgeview 258 u; the Port issues its own permits). Together 1,198 u.
- **Occupied towers DBI never closed, and that the certificate dataset lacks.** 301 Beale (status "issued"), 338 Main,
  88 Arkansas (issued 2016), 160 Folsom ("expired"), 88 Broadway ("filed").
- **Phased towers our certificate rule undercounts:** 500 Folsom 526 vs 1,071, 41 Tehama 84 vs 403, 801 Brannan 120 vs 434.
  Certificates issued before 2018, or an APR that reports a whole building at its first TCO. Not resolved.
- **Ours, wrong:** about 1,000 u of hotel and alteration phantoms still pass (855 Brannan 434, 701 3rd St 230, 1095
  Market 203). SF's alteration permits on new towers record `existing_units = 0`, `proposed_units` = the building.

## What a second city actually needed (the honest answer to "change two values")
1. **Every notebook's config, not one.** JN3–JN6b each reload the raw Berkeley spreadsheets with Berkeley's column names.
2. **A column adapter (the real work).** SF has no `UnitsAdded` or `Work Type`: New ← permit_type 1/2; UnitsAdded ←
   proposed − existing on types 1–3 only; keep primary-address rows (SF repeats a permit per address).
3. **The shared housing filter treats R-1 (hotel) as housing.** In SF, hotels with mixed occupancy still pass (701 3rd St
   230 rooms, 1095 Market 203); not measured in Berkeley.
4. **A second completion source.** SF's permit table leaves occupied towers open; its occupancy record is a separate dataset.
5. **APN code, not a registry row.** `housing_rules.to_canonical_apn` is hard-wired to Alameda's 4 segments; SF block-lot
   needed a new parser (scratch).
6. **`cycle_for_date` raises on first permits before 2015-01-31** (72 SF completions; Berkeley's feed starts in 2018).
7. **The scorecard should join by address, then APN, then permit number.** Address-only buckets split one building into
   a "found" and a "coverage" (101 Hayes in the APR is 150 Van Ness at DBI).
8. **Every checkpoint is pinned to Berkeley numbers and addresses** (1385, 951, 4310, 2352 Shattuck).
9. **Affects Berkeley too: HCD renamed `CO_EXTREMELY_INCOME_NDR` to `CO_EXTREMELY_LOW_INCOME_NDR`** after the 2026-06-17
   pull; JN6a/JN6b's SQL fails on any fresh pull.
- Unchanged and city-neutral: `net_units`'s logic, the address key and `matches()`, the MAX-not-SUM fold, stage derived
  from dated events, ABAG cycle dates (shared by SF; a southern city would need its own), the scorecard's invariant.

## Candidate next steps (none started)
- Fix item 9 in JN6a/JN6b now (Berkeley breaks on a fresh pull).
- One CITY config cell read by every notebook (item 1); register SF in `APN_FORMATS` with a block-lot parser (item 5).
- Decide whether R-1 belongs in `is_housing` (item 3): it would change Berkeley's v3 numbers, so a gated, measured change.
- A CPRA to SF DBI is unnecessary; a follow-up would be Planning's Housing Inventory for the phased towers.
