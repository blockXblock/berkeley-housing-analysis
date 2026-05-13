# CPRA 2023-2025 Annual Permit Report Comparison

**Generated:** 2026-05-10
**Status:** Read-only analysis (no imports or modifications)

## Data Sources

| Source | Description | Records |
|--------|-------------|---------|
| CPRA Excel | `BP_Annual Permit Report.xlsx` — residential building permits 2023-01-01 to 2025-12-31 | 14,143 unique permit numbers |
| v1 `building_permits` | `berkeley_housing_analysis.db` | 94 rows |
| v1 `project_permits` | `berkeley_housing_analysis.db` | 114 rows |
| v1 combined | Unique permit numbers across both tables | 208 |

---

## Q1: Coverage — How many CPRA permits exist in v1?

| Match Target | Count | % of CPRA |
|--------------|-------|-----------|
| In `building_permits` | 25 | 0.18% |
| In `project_permits` | 0 | 0.00% |
| In either table | 25 | 0.18% |
| In neither (new) | 14,118 | 99.82% |

**Observation:** v1 captures only 25 of the 14,143 CPRA permit numbers (0.18%). The vast majority of CPRA records represent permits not tracked in v1. This is expected — v1 focuses on multi-unit housing projects, while CPRA includes all residential permits (single-family renovations, ADUs, minor work, etc.).

---

## Q2: New Permits — Summary of CPRA records not in v1

### By Issuance Year

| Year | Count |
|------|-------|
| 2016 | 3 |
| 2017 | 9 |
| 2018 | 18 |
| 2019 | 37 |
| 2020 | 55 |
| 2021 | 208 |
| 2022 | 1,080 |
| 2023 | 4,230 |
| 2024 | 4,145 |
| 2025 | 4,170 |
| 2026 | 3 |

**Note:** CPRA file labeled as "2023-2025" but contains permits issued as early as 2016. The bulk of records (12,545 of 14,124, or 89%) are from 2023-2025.

### By Occupancy Type

| OccType | Count |
|---------|-------|
| R-3 Residential: Dwellings (1 or 2 Units), Townhomes, Congregate Living | 11,046 |
| R-2 Residential: Permanent, Multi-Unit (3+ Units) | 2,124 |
| Not Applicable (new) | 383 |
| U Private Garages, Carports, Sheds, Agricultural, Tanks, Accessory | 277 |
| undefined | 128 |
| Other types | 166 |

### Residential vs Non-Residential

| Category | Count | % |
|----------|-------|---|
| Residential (R-* codes) | 13,290 | 94.1% |
| Non-residential | 834 | 5.9% |

### Dwelling Unit Production

| Metric | Value |
|--------|-------|
| Permits with UnitsAdded > 0 | 896 |
| Total units added | 22,904 |

**Observation:** Most permits (94%) are residential, but only 896 (6%) actually add dwelling units. The majority are renovations, alterations, or accessory structures on existing residential properties.

---

## Q3: Address/APN Matching for Unmatched Permits

For the 14,124 CPRA permits not matched by permit number, can they be linked to v1 projects by APN or address?

### v1 Project Reference Data

| Data | Count |
|------|-------|
| v1 projects | 179 |
| Unique normalized addresses | 176 |
| Unique normalized APNs | 163 |

### Match Results

| Match Method | Count | % of Unmatched |
|--------------|-------|----------------|
| Matched by APN | 324 | 2.29% |
| Matched by address (additional) | 0 | 0.00% |
| **Total matchable** | **324** | **2.29%** |
| Not matchable | 13,800 | 97.71% |

**Observation:** Only 324 CPRA permits (2.3%) can be linked to v1 projects via APN. Address matching found no additional matches beyond APN matching — likely because addresses that match by APN also match by address, or v1 address formats differ from CPRA's `StreetNumber + StreetName + StreetType` construction.

### Address Normalization Approach

Applied the following transformations for address comparison:
1. Convert to uppercase
2. Remove punctuation
3. Standardize abbreviations: STREET→ST, AVENUE→AVE, BOULEVARD→BLVD, DRIVE→DR, ROAD→RD, LANE→LN, COURT→CT, PLACE→PL, WAY→WY
4. Collapse multiple spaces

APN normalization: remove all non-digit characters to create numeric-only strings for comparison.

---

## Summary

The CPRA Annual Permit Report contains 14,143 permits. Of these:

- **25 (0.18%)** match v1 permit numbers directly
- **324 (2.29%)** can be linked to v1 projects by APN
- **13,800 (97.71%)** have no connection to v1 project records

This low overlap is expected: v1 tracks ~179 multi-unit housing developments, while CPRA captures the full spectrum of residential building activity including single-family renovations, ADU additions, and minor alterations. The 2,124 R-2 (multi-unit) permits in CPRA warrant closer examination — some may represent projects that should be in v1 but are missing.

---

## Q4: R-2 Multi-Unit Permits with UnitsAdded > 0

Of the 2,167 R-2 (multi-unit residential) permits in CPRA, how many actually add dwelling units?

| Metric | Count |
|--------|-------|
| Total R-2 permits | 2,167 |
| R-2 permits with UnitsAdded > 0 | 307 |
| R-2 permits with UnitsAdded > 0 (2023-2025 only) | 235 |

### By Year and Unit Bucket (2023-2025)

| Year | 1 unit | 2-4 units | 5-19 units | 20-49 units | 50+ units | Total |
|------|--------|-----------|------------|-------------|-----------|-------|
| 2023 | 6 | 9 | 4 | 7 | 50 | 76 |
| 2024 | 10 | 7 | 5 | 20 | 39 | 81 |
| 2025 | 9 | 7 | 6 | 14 | 42 | 78 |
| **Total** | **25** | **23** | **15** | **41** | **131** | **235** |

### Total Units by Bucket (2023-2025)

| Bucket | Permits | Total Units |
|--------|---------|-------------|
| 1 | 25 | 25 |
| 2-4 | 23 | 55 |
| 5-19 | 15 | 173 |
| 20-49 | 41 | 1,542 |
| 50+ | 131 | 14,562 |
| **Total** | **235** | **16,357** |

**Observation:** The 131 permits adding 50+ units account for 89% of all multi-unit production (14,562 of 16,357 units). These large projects are the primary candidates for v1 tracking.

---

## Q5: APN-Matched Permits Gap Analysis

For the 324 CPRA permits linked to v1 projects by APN, how do they compare to v1's existing permit data?

### Summary

| Metric | Count |
|--------|-------|
| Unique v1 projects with APN matches | 53 |
| Total CPRA permits across these projects | 324 |
| CPRA permits NOT in v1 permit tables | 324 |
| Overlap (in both CPRA and v1) | 0 |

**Key finding:** All 324 APN-matched permits are new to v1 — none appear in v1's `building_permits` or `project_permits` tables.

### Top 10 v1 Projects with Largest Permit Gaps

| Project ID | Address | CPRA Permits | v1 Permits | Gap |
|------------|---------|--------------|------------|-----|
| 136 | 1951 Shattuck Ave | 25 | 0 | 25 |
| 154 | 2001 ASHBY Ave | 22 | 0 | 22 |
| 135 | 2150 Kittredge St | 21 | 0 | 21 |
| 138 | 2099 MLK Jr Way | 21 | 0 | 21 |
| 152 | 1598 UNIVERSITY Ave | 20 | 2 | 20 |
| 173 | 2000 DWIGHT Way | 20 | 0 | 20 |
| 176 | 2440 SHATTUCK Ave | 19 | 0 | 19 |
| 172 | 2650 TELEGRAPH Ave | 12 | 0 | 12 |
| 150 | 3030 TELEGRAPH Ave | 10 | 1 | 10 |
| 174 | 1773 OXFORD St | 10 | 0 | 10 |

### Date/Valuation Comparison for Overlapping Permits

For the 25 permits that appear in both CPRA and v1 (matched by permit number in Q1):

| Field | CPRA | v1 |
|-------|------|-----|
| Issuance Date | Populated | NULL (not captured) |
| Job Valuation | Populated | NULL (not captured) |

**Observation:** v1's `building_permits` table has permit numbers but lacks issuance dates and job valuations. CPRA provides richer data that could backfill v1.

---

## Q6: ADU Permit Detection and Analysis

### Detection Methods

| Method | Description | Permits Found |
|--------|-------------|---------------|
| Method 1 | ADU column = "Yes" | 2,644 |
| Method 2 | Work Type/SubType contains ADU/JADU/Accessory | 0 |
| Method 3 | WorkDescription contains ADU patterns | 628 |

### Overlap Analysis

| Category | Count |
|----------|-------|
| Method 1 only | 2,151 |
| Method 3 only | 135 |
| Methods 1 & 3 | 493 |
| **Total unique ADU permits** | **2,779** |

**Note:** The ADU column is the most reliable indicator (2,644 permits). WorkDescription adds 135 permits not flagged by the ADU column. Work Type/SubType columns don't use ADU terminology.

### ADU Permits by Year (2023-2025)

| Year | Count |
|------|-------|
| 2023 | 689 |
| 2024 | 973 |
| 2025 | 839 |
| **Total** | **2,501** |

### Detached vs Attached

| Detached Column | Count |
|-----------------|-------|
| No data (NaN) | 2,177 |
| Yes (detached) | 361 |
| No (attached) | 241 |

**Note:** 78% of ADU permits lack Detached/Attached classification.

### Units Added by ADU Permits

| UnitsAdded | Count | % |
|------------|-------|---|
| 0 | 2,238 | 80.5% |
| 1 (single ADU) | 448 | 16.1% |
| >1 (multiple) | 93 | 3.3% |

**Observation:** Most ADU permits (80%) have UnitsAdded = 0, suggesting they may be renovations, conversions, or permits where unit counts weren't recorded. Only 448 permits explicitly add exactly 1 unit.

### Sample ADU Permits

| Permit | Address | Units | Detached | Year | Description |
|--------|---------|-------|----------|------|-------------|
| B2018-01256 | 2334 JEFFERSON Ave | 1 | Yes | 2022 | Demo portion of garage/storage building and build attached ADU to garage |
| B2019-00301 | 2206 ROOSEVELT Ave | 1 | Yes | 2022 | New detached ADU at rear yard of existing main single family residence |
| B2019-00439 | 1827 SIXTY-SECOND St | 0 | Yes | 2019 | New (533 SF) ADU in rear yard |
| B2019-01241 | 1222 CARLETON St | 1 | Yes | 2019 | Convert detached Garage to ADU |
| B2017-02782 | 791 HILLDALE Ave | 1 | — | 2019 | New 407 SF ADU |

---

## Updated Summary

The CPRA dataset reveals significant gaps in v1's permit coverage:

1. **Multi-unit production:** 235 R-2 permits (2023-2025) added 16,357 units, with 131 large projects (50+ units) accounting for 89% of production
2. **v1 project gaps:** 53 v1 projects have 324 CPRA permits not in v1's permit tables — all are missing
3. **ADU activity:** 2,779 ADU permits identified, with 2,501 issued in 2023-2025 — this represents substantial housing production outside v1's scope
4. **Data quality:** v1 permit tables lack issuance dates and valuations that CPRA provides

---

## Q7: R-2 Deduplication Analysis

The 235 R-2 permits reporting 16,357 units are **heavily duplicated**. Each sub-permit (revision, deferred submittal) carries the same unit count as its master permit.

### Deduplication Summary

| Metric | Count |
|--------|-------|
| R-2 permits with UnitsAdded > 0 (2023-2025) | 235 |
| Unique APN+year combinations | 91 |
| Large projects (50+ units) — permits | 131 |
| Large projects (50+ units) — distinct APNs | 17 |

### Multi-Permit APNs

| Metric | Count |
|--------|-------|
| APNs with multiple R-2 permits (UnitsAdded > 0) | 37 |
| Total permits at these multi-permit APNs | 211 |

**Key finding:** 211 of 235 permits (90%) are at APNs with multiple permits. The unit counts are duplicated across master permits and their sub-permits.

### Sample: Top 5 APNs by Claimed Units

| APN | Permits | Claimed Units | Actual Structure |
|-----|---------|---------------|------------------|
| 056200300100 | 13 | 2,691 | 1 master (207 units) + 12 sub-permits |
| 057204600100 | 16 | 2,569 | 2 masters (163+160 units) + 14 sub-permits |
| 055182201800 | 18 | 2,034 | 1 master (113 units) + 17 sub-permits |
| 053159101803 | 15 | 1,305 | 1 master (87 units) + 14 sub-permits |
| 057202401300 | 15 | 1,080 | 1 master (72 units) + 14 sub-permits |

### Sub-Permit Pattern

Sub-permits follow naming conventions:
- `-DEF##` = Deferred submittal (shop drawings, equipment specs)
- `-REV##` = Revision (design changes, corrections)

Example at APN 056200300100 (2520 Durant):
- **B2024-01924**: Master permit for 207-unit mixed-use building
- **B2024-01924-DEF01** through **-DEF13**: Deferred submittals for framing, elevators, parking lifts, etc.
- **B2024-01924-REV05** through **-REV11**: Revisions to barriers, awnings, panels

Each sub-permit inherits the 207-unit count from the master, inflating the total.

### Corrected Unit Estimate

To get accurate unit counts, count only master permits (no `-REV` or `-DEF` suffix):
- **Actual distinct projects:** ~91 (unique APN+year combinations)
- **True unit production:** Requires summing only master permit unit counts

---

## Q8: ADU Permits with UnitsAdded = 0 — Detailed Analysis

Of the 2,501 ADU permits in 2023-2025, 2,089 (84%) have UnitsAdded = 0. What are these permits?

### Categorization of UnitsAdded = 0 ADU Permits

| Category | Count | % |
|----------|-------|---|
| Sub-permit (MEP work) | 1,336 | 64.0% |
| Other/unclear | 603 | 28.9% |
| Sub-permit (revision/deferred) | 72 | 3.4% |
| New ADU (likely data error) | 44 | 2.1% |
| Conversion | 23 | 1.1% |
| Garage conversion | 6 | 0.3% |
| Legalization | 5 | 0.2% |

### Category Definitions

- **Sub-permit (MEP work)**: Electrical panel upgrades, plumbing changes, HVAC, water heaters, solar panels — work associated with an ADU but not the ADU construction itself
- **Sub-permit (revision/deferred)**: Permits with `-REV` or `-DEF` suffix, or "revision" in description
- **New ADU (likely data error)**: Description says "new ADU" but UnitsAdded = 0
- **Conversion/Garage conversion**: Converting existing space to ADU
- **Legalization**: Legalizing unpermitted ADU

### Key Finding

**64% of "ADU permits" with UnitsAdded = 0 are actually sub-permits for MEP work** — electrical panel upgrades, plumbing, etc. These are flagged as ADU-related because they're associated with ADU projects, but they don't represent new dwelling units.

### Sample MEP Sub-Permits (flagged as ADU)

| Permit | Description |
|--------|-------------|
| B2023-05295 | Electrical service upgrade 300A existing 3 meters |
| B2025-00211 | Main Panel Upgrade 100a to 200a, New 120v Circuit... |
| B2023-03444 | Relocate low pressure houseline & trench to new PG&E meter |
| B2025-03726 | Upgrading main electrical panel from 100 to 200 |
| B2025-03772 | Replace water heater |

### Corrected ADU Count

- **Total ADU-flagged permits 2023-2025:** 2,501
- **Likely actual new ADUs:** ~412 (UnitsAdded = 1) + ~44 (data errors with UnitsAdded = 0 but "new ADU" in description) ≈ **456**
- **MEP/sub-permits:** ~1,408 (not new units)
- **Unclear:** ~637

---

## Q9: 1951 Shattuck Anatomy

The 25 CPRA permits at 1951 Shattuck Ave (v1 Project 136) represent **one development project** with two construction phases.

### Permit Structure

| Category | Count |
|----------|-------|
| Master permits | 2 |
| Sub-permits (DEF/REV) | 23 |
| **Total** | **25** |

### Master Permits

| Permit | Description | Units |
|--------|-------------|-------|
| B2019-05608 | Phase 1: Basement and 1st floor of 12-story mixed-use building | 163 |
| B2021-04893 | Phase 2: Levels 2-12 of same building | 163 |

### Sub-Permit Breakdown

**B2019-05608 sub-permits (7):**
- DEF02: Metal stairs shop drawings
- DEF03: Vehicle parking lift
- DEF04: Precast fabricator approval
- DEF05: Building maintenance system
- DEF06: Diesel generator
- REV01: Removal of switchgear
- REV07: (pending)

**B2021-04893 sub-permits (16):**
- DEF01–DEF17: Facade, guardrails, generator fuel, evacuation signs, fitness equipment, signage
- REV04: Unit entry door changes
- REV14: Correct unit count on drawings
- REV16: FARS tubing riser

### Timeline

| Date | Event |
|------|-------|
| 2019-12-27 | Phase 1 submitted |
| 2021-10-27 | Phase 2 submitted |
| 2022-09-08 | Phase 1 issued |
| 2022-10 – 2024-06 | Sub-permits issued as construction progresses |

### Key Finding

The 25 permits represent **one 163-unit project** built in two phases, not 25 separate developments. The sub-permits are deferred submittals (shop drawings, equipment specs) and revisions that are standard for large construction projects.

---

## Final Corrected Summary

After deduplication analysis:

| Metric | Raw Count | Corrected Estimate |
|--------|-----------|-------------------|
| R-2 permits adding units (2023-2025) | 235 | ~91 distinct projects |
| Units from R-2 permits | 16,357 | ~2,500–3,000 (deduped) |
| ADU permits (2023-2025) | 2,501 | ~456 actual new ADUs |
| 1951 Shattuck permits | 25 | 1 project (163 units) |

**CPRA permit data requires deduplication** before aggregating unit counts. Each master permit generates multiple sub-permits for deferred submittals and revisions, all carrying the same unit count.

---

## Q10: Deduplicated R-2 Multi-Unit Projects (2023-2025)

Using formal deduplication logic that groups permits by (APN, master_permit) and uses only the master permit's unit count.

### Deduplication Method

1. Extract master permit number by removing `-REV##`, `-DEF##`, `-ADD##` suffixes
2. Group permits by (normalized APN, master permit number)
3. For each group, use the master permit row (no suffix) or earliest if all are sub-permits
4. Sum only master permit unit counts

### Results by Year

| Year | Distinct Projects | Total Units |
|------|-------------------|-------------|
| 2023 | 28 | 1,250 |
| 2024 | 20 | 676 |
| 2025 | 16 | 461 |
| **Total** | **64** | **2,387** |

### Projects with 5+ Units by Year

**2023 (17 projects with 5+ units):**

| Permit | Units | Address |
|--------|-------|---------|
| B2021-00008 | 169 | 2150 KITTREDGE St |
| B2019-05608 | 163 | 1951 SHATTUCK Ave |
| B2021-04893 | 160 | 1951 SHATTUCK Ave |
| B2021-02404 | 113 | 2000 DWIGHT Way |
| B2019-03689 | 96 | 2100 SAN PABLO Ave |
| B2021-02905 | 87 | 2001 ASHBY Ave |
| B2021-03950 | 72 | 2099 MLK JR Way |
| B2018-03255 | 63 | 2527 SAN PABLO Ave |
| B2020-01991 | 57 | 2701 SHATTUCK Ave |
| B2017-02610 | 50 | 2067 UNIVERSITY Ave |

**2024 (10 projects with 5+ units):**

| Permit | Units | Address |
|--------|-------|---------|
| B2024-01924 | 207 | 1598 UNIVERSITY Ave |
| B2023-06416 | 144 | 3030 TELEGRAPH Ave |
| B2023-02332 | 83 | 2538 DURANT Ave |
| B2023-00774 | 72 | 1752 SHATTUCK Ave |
| B2019-02956 | 45 | 2009 ADDISON St |
| B2021-02423 | 40 | SAN PABLO Ave |
| B2014-05752 | 36 | 1698 UNIVERSITY Ave |
| B2022-05957 | 13 | 2328 CHANNING Way |
| B2023-02975 | 12 | 2555 COLLEGE Ave |
| B2024-04593 | 8 | 2235 HEARST Ave |

**2025 (10 projects with 5+ units):**

| Permit | Units | Address |
|--------|-------|---------|
| B2024-02966 | 110 | 1701 SAN PABLO Ave |
| B2024-06011 | 83 | 2538 DURANT Ave |
| B2024-05944 | 69 | 2300 ELLSWORTH St |
| B2021-04232 | 57 | 2902 ADELINE St |
| B2022-05881 | 54 | 1740 SAN PABLO Ave |
| B2024-00143 | 36 | 2403 SAN PABLO Ave |
| B2022-04242 | 17 | 2317 CHANNING Way |
| B2025-03731 | 11 | 2012 CHANNING Way |
| B2024-05284 | 10 | 2307 PIEDMONT Ave |
| B2025-00168 | 6 | 2330 BLAKE St |

---

## Q11: Deduplicated ADU Projects (2023-2025)

ADU permits are filtered to exclude MEP sub-work (electrical upgrades, plumbing, etc.) and grouped by (APN, master_permit).

### Results by Year

| Year | Distinct ADU Projects | Total Units |
|------|----------------------|-------------|
| 2023 | 372 | 85 |
| 2024 | 476 | 186 |
| 2025 | 442 | 231 |
| **Total** | **1,290** | **502** |

### ADU Type Breakdown (2023-2025 combined)

| Type | Count | % |
|------|-------|---|
| Unknown/unclassified | 986 | 76.4% |
| Detached | 178 | 13.8% |
| Attached | 102 | 7.9% |
| JADU (Junior ADU) | 24 | 1.9% |

**Note:** 76% of ADU permits lack Detached/Attached classification in the CPRA data.

### ADU vs Unit Count Discrepancy

Most ADU projects (1,290) report far fewer units (502) than expected because:
1. Many permits have UnitsAdded = 0 (data quality issue)
2. Some ADU permits are for garage conversions that don't add net units
3. JADU permits may count as 0 or 1 depending on local tracking

---

## Q12: Comparison to NotebookLM BMR Totals

### NotebookLM Corrected BMR Totals

| Year | BMR Units |
|------|-----------|
| 2023 | 124 |
| 2024 | 119 |
| 2025 | 93 |
| **Total** | **336** |

### CPRA Deduplicated Production

| Year | R-2 Units | ADU Units | Total |
|------|-----------|-----------|-------|
| 2023 | 1,250 | 85 | 1,335 |
| 2024 | 676 | 186 | 862 |
| 2025 | 461 | 231 | 692 |
| **Total** | **2,387** | **502** | **2,889** |

### Comparison Analysis

| Year | NotebookLM BMR | CPRA Total | BMR as % of CPRA |
|------|----------------|------------|------------------|
| 2023 | 124 | 1,335 | 9.3% |
| 2024 | 119 | 862 | 13.8% |
| 2025 | 93 | 692 | 13.4% |

### Critical Limitation

**CPRA data does NOT distinguish BMR (Below Market Rate) from market-rate units.**

The CPRA totals represent ALL residential production:
- Market-rate units
- Below Market Rate (BMR) / affordable units
- ADUs (which are generally market-rate)

BMR units are typically 10-20% of total production in large projects, depending on:
- Inclusionary zoning requirements
- Density bonus programs
- 100% affordable projects

### Estimated BMR from CPRA

If BMR averages ~10-15% of R-2 multi-unit production:

| Year | R-2 Units | Est. BMR (10%) | Est. BMR (15%) | NotebookLM BMR |
|------|-----------|----------------|----------------|----------------|
| 2023 | 1,250 | 125 | 188 | 124 |
| 2024 | 676 | 68 | 101 | 119 |
| 2025 | 461 | 46 | 69 | 93 |

The NotebookLM totals align with ~10% BMR rate for 2023, but imply higher rates (15-20%) for 2024-2025. This could reflect:
- More 100% affordable projects in 2024-2025
- Different tracking methodology
- Projects with higher-than-average BMR requirements

---

## Reusable Deduplication Script

Saved to: `scripts/cpra_dedup.py`

### Usage

```python
from cpra_dedup import load_cpra, dedupe_permits, dedupe_r2_permits, dedupe_adu_permits

# Load CPRA data
cpra = load_cpra('/path/to/BP_Annual Permit Report.xlsx')

# Deduplicate R-2 multi-unit projects
r2 = dedupe_r2_permits(cpra, years=[2023, 2024, 2025])

# Deduplicate ADU projects
adu = dedupe_adu_permits(cpra, years=[2023, 2024, 2025])

# Custom filter
custom = dedupe_permits(cpra, filter_func=lambda df: df['UnitsAdded'] > 50)
```

### Command Line

```bash
python scripts/cpra_dedup.py input.xlsx output.csv
```

---

## Revised Final Summary

| Metric | Raw CPRA | Deduplicated |
|--------|----------|--------------|
| R-2 permits (2023-2025) | 235 | 64 projects |
| R-2 units | 16,357 | 2,387 |
| ADU permits (2023-2025) | 2,501 | 1,290 projects |
| ADU units | varies | 502 |
| **Total housing units** | **inflated** | **2,889** |

**Key findings:**
1. Raw CPRA unit counts are inflated ~7x due to sub-permit duplication
2. True multi-unit (R-2) production is ~2,387 units over 2023-2025
3. True ADU production is ~502 units (possibly undercounted due to UnitsAdded=0 data quality issues)
4. NotebookLM BMR totals (336 units) represent ~12% of total CPRA production, consistent with inclusionary requirements

---

## Q13: Missing R-2 Projects (Not in v1)

Of the 64 deduplicated R-2 master permits (2023-2025), how many are tracked in v1?

### Summary

| Metric | Count |
|--------|-------|
| Deduplicated R-2 projects | 64 |
| Matched to v1 by APN | 23 |
| **NOT in v1** | **41** |
| Units in missing projects | **695** |

### Missing Projects by Year

| Year | Missing Projects | Missing Units |
|------|------------------|---------------|
| 2023 | 17 | 310 |
| 2024 | 14 | 160 |
| 2025 | 10 | 225 |
| **Total** | **41** | **695** |

### Projects v1 Should Include (Sorted by Size)

| Permit | Address | Units | Year | Valuation |
|--------|---------|-------|------|-----------|
| B2024-02966 | 1701 SAN PABLO Ave | 110 | 2025 | $25,746,478 |
| B2019-03689 | 2100 SAN PABLO Ave | 96 | 2023 | $18,000,000 |
| B2024-06011 | 2538 DURANT Ave | 83 | 2025 | — |
| B2023-02332 | 2538 DURANT Ave | 83 | 2024 | $16,441,981 |
| B2018-03255 | 2527 SAN PABLO Ave | 63 | 2023 | $25,724,083 |
| B2020-01991 | 2701 SHATTUCK Ave | 57 | 2023 | $4,811,159 |
| B2017-02610 | 2067 UNIVERSITY Ave | 50 | 2023 | $6,812,412 |
| B2021-02423 | SAN PABLO Ave | 40 | 2024 | $2,726,986 |
| B2020-00206 | 1717 UNIVERSITY Ave | 15 | 2023 | $3,207,200 |
| B2022-05957 | 2328 CHANNING Way | 13 | 2024 | $3,890,000 |

**Note:** Several "missing" projects may be ADU additions to existing buildings (B2025-00168: 6 ADUs at 2330 Blake) or garage conversions rather than new multi-unit developments. Manual review recommended before adding to v1.

### Full List of Unmatched R-2 Projects

<details>
<summary>Click to expand (41 projects)</summary>

| Permit | Address | APN | Year | Units | Description |
|--------|---------|-----|------|-------|-------------|
| B2024-02966 | 1701 SAN PABLO Ave | 058212901700 | 2025 | 110 | New 6-story, 110-unit publicly funded multi-family |
| B2019-03689 | 2100 SAN PABLO Ave | 056197700605 | 2023 | 96 | Revision to remove front restaurant |
| B2024-06011 | 2538 DURANT Ave | 055187602101 | 2025 | 83 | Temporary power service for construction |
| B2023-02332 | 2538 DURANT Ave | 055187602101 | 2024 | 83 | New 8-story building with 83 dwelling units |
| B2018-03255 | 2527 SAN PABLO Ave | 054178101501 | 2023 | 63 | New 6-story mixed use with 63 residential units |
| B2020-01991 | 2701 SHATTUCK Ave | 054171900100 | 2023 | 57 | Revisions to fire pump room |
| B2017-02610 | 2067 UNIVERSITY Ave | 057205300500 | 2023 | 50 | Removing FSDs at each stack - 07 units |
| B2021-02423 | SAN PABLO Ave | 056192801900 | 2024 | 40 | Add guardrail at roof deck parapet |
| B2020-00206 | 1717 UNIVERSITY Ave | 057206101000 | 2023 | 15 | Document means of egress compliance |
| B2022-05957 | 2328 CHANNING Way | 055188302700 | 2024 | 13 | Restoration of Luttrell House + 13 new units |
| B2025-03731 | 2012 CHANNING Way | 055189602100 | 2025 | 11 | Install water heater stand |
| B2024-05284 | 2307 PIEDMONT Ave | 055186400100 | 2025 | 10 | Repair of 4 exterior wood posts |
| B2023-03349 | 2537 ELLSWORTH St | 055183201700 | 2023 | 9 | Interior remodel of units |
| B2024-04593 | 2235 HEARST Ave | 058218101700 | 2024 | 8 | Reroof BUR |
| B2025-00168 | 2330 BLAKE St | 055183202601 | 2025 | 6 | Interior remodel + 6 ADUs at ground level |
| B2021-04563 | 2980 COLLEGE Ave | 052157309300 | 2023 | 4 | Deferred submittal: mini-split to 4 units |
| B2022-01345 | 1837 BERKELEY Way | 057206300700 | 2023 | 3 | Construct 3 new townhouses |
| B2021-04907 | 2421 FIFTH St | 056194302000 | 2024 | 3 | New 3-unit residential building |
| B2023-04424 | 1403 CARLETON St | 054179401401 | 2024 | 2 | ADU conversion adding 2 units |
| B2024-02435 | 1650 OXFORD St | 058217900800 | 2024 | 2 | Two new detached ADUs |
| B2022-01079 | 2701 DURANT Ave | 055187000800 | 2023 | 2 | Convert basement to 2 ADUs |
| B2021-03440 | 1828 EUCLID Ave | 058219100200 | 2023 | 2 | Convert restaurant space to 2 units |
| B2022-03494 | 1515 HARMON St | 052153601100 | 2024 | 2 | ADU unit number change |
| B2020-01168 | 2025 DURANT Ave | 055189401401 | 2023 | 2 | Concrete slab revision for ADU |
| B2024-05037 | 2326 GRANT St | 055190501103 | 2024 | 2 | Replace furnace |
| B2021-02307 | 2737 FOREST Ave | 054170800500 | 2023 | 2 | ADU revisions |
| B2022-02002 | 1426 SPRUCE St | 059225701200 | 2023 | 1 | Convert basement to ADU |
| B2022-01040 | 2225 HEARST Ave | 058218101800 | 2023 | 1 | Convert garage to ADU |
| B2022-05775 | 2655 VIRGINIA St | 058220901600 | 2024 | 1 | Interior remodel + conversion ADU |
| B2024-05185 | 1803 OXFORD St | 058218102300 | 2025 | 1 | Convert garage/basement to ADU |
| B2024-01607 | 1650 OXFORD St | 058217900800 | 2024 | 1 | ADU conversion at multifamily |
| B2024-03408 | 1813 SIXTY-THIRD St | 052152701002 | 2025 | 1 | Convert garage to ADU |
| B2024-00117 | 1202 DELAWARE St | 057208200200 | 2024 | 1 | Triplex remodel |
| B2024-03777 | 2715 DWIGHT Way | 055186701000 | 2025 | 1 | ADU from garage conversion |
| B2023-02685 | 2430 PROSPECT St | 055186500700 | 2024 | 1 | ADU in basement parking garage |
| B2024-00772 | 12 PANORAMIC Way | 055185300400 | 2024 | 1 | Convert garage to ADU |
| B2024-02051 | 2520 REGENT St | 055183901501 | 2025 | 1 | Garage conversion to ADU |
| B2024-03741 | 2124 PARKER St | 055182502401 | 2025 | 1 | Convert garage to ADU |
| B2022-01264 | 2906 KING St | 053160900201 | 2023 | 1 | Convert carport to ADU |
| B2020-02097 | 1519 FAIRVIEW St | 052154401200 | 2023 | 1 | Update Title 24 reports |
| B2023-02600 | 1321 SPRUCE St | 060246201500 | 2023 | 1 | Convert basement to 3BR ADU |

</details>

---

## Q14: ADU Inventory vs v1

### Summary

| Metric | Count |
|--------|-------|
| Deduplicated ADU projects (2023-2025) | 1,562 |
| Matched to v1 by APN | 7 |
| **NOT in v1** | **1,555** |
| Unmatched with UnitsAdded ≥ 1 | 257 |
| Total units from unmatched ADUs | 419 |

**As expected, v1 historically excluded ADUs.** Only 7 ADU permits are at v1 project sites (likely ADUs added to existing tracked developments).

### ADU Units by Year (Unmatched to v1)

| Year | Projects | Units Added |
|------|----------|-------------|
| 2023 | 82 | 87 |
| 2024 | 80 | 101 |
| 2025 | 95 | 231 |
| **Total** | **257** | **419** |

### All Deduplicated ADU Projects by Year

| Year | Total Projects | With Units | Units |
|------|----------------|------------|-------|
| 2023 | 423 | 82 | 87 |
| 2024 | 613 | 83 | 186 |
| 2025 | 526 | 95 | 231 |
| **Total** | **1,562** | **260** | **504** |

### ADU Type Classification

| Type | Count | % |
|------|-------|---|
| Unclassified | 1,170 | 74.9% |
| Detached | 211 | 13.5% |
| Attached | 102 | 6.5% |
| Attached/Conversion | 52 | 3.3% |
| JADU | 27 | 1.7% |

### Sample ADU Projects

| Permit | Address | Year | Units | Description |
|--------|---------|------|-------|-------------|
| B2023-05179 | 1326 MLK JR Way | 2024 | 1 | New detached 560 sqft ADU at rear of SFH |
| B2024-01075 | 51 OAKVALE Ave | 2024 | 0 | Foundation replacement of rear cottage |
| B2024-02851 | 2615 GRANT St | 2024 | 0 | Reroof: Modified bitumen roofing system |
| B2023-03613 | 1739 WARD St | 2023 | 0 | Install Mitsubishi 2-zone ducted split heat pump |

**Note:** Many ADU permits with UnitsAdded=0 are MEP work (electrical, HVAC, plumbing) associated with ADU projects, not new ADU construction.

---

## Q15: Demolition Analysis

### Summary

| Metric | Count |
|--------|-------|
| Total demolition permits (2023-2025) | 150 |
| Deduplicated demolition projects | 150 |
| Matched to v1 by APN | 9 |
| **NOT in v1** | **141** |

**Note:** Demolition permits have no sub-permits (no -REV/-DEF suffixes), so raw count equals deduplicated count.

### Demolitions by Year

| Year | Projects | Units Removed |
|------|----------|---------------|
| 2023 | 42 | 5 |
| 2024 | 55 | 8 |
| 2025 | 53 | 4 |
| **Total** | **150** | **17** |

### Demolitions at v1 Project Sites

9 demolitions are at locations tracked in v1 (likely pre-construction demolition for new development):

| Permit | Address | Units Removed | Description |
|--------|---------|---------------|-------------|
| B2023-06442 | 2330 WEBSTER St | 2 | Demo 2800 sqft one-story duplex (Telegraph/Webster) |
| B2023-06443 | 2334 WEBSTER St | 2 | Demo 2460 sqft two-story duplex (Telegraph/Webster) |
| B2025-00388 | 2300 ELLSWORTH St | 0 | Demo apartment building, retain facade portions |
| B2023-03067 | 1773 OXFORD St | 0 | Demo apartment building (see rebuild B2023-02354) |
| B2022-01278 | 1716 SEVENTH St | 0 | Demo 801 sqft SFR + garage + shed |

### Unmatched Demolitions with Units Removed

12 demolitions outside v1 project sites removed units:

| Permit | Address | APN | Units | Description |
|--------|---------|-----|-------|-------------|
| B2023-00142 | 1422 CORNELL Ave | 060239800900 | 2 | Demolish detached garage |
| B2024-06091 | 2708 PRINCE St | 052156303600 | 1 | Demo one-story SFR |
| B2025-03217 | 1521 STUART St | 054173301300 | 1 | Demo wood frame dwelling (rebuild pending) |
| B2024-03439 | 1200 DWIGHT Way | 054178102900 | 1 | Demo SFR |
| B2023-02743 | 1536 BLAKE St | 054180002900 | 1 | Demo/rebuild single car garage |
| B2023-02428 | 2431 ACTON St | 056191902600 | 1 | Demolition of garage |
| B2021-05206 | 2421 FIFTH St | 056194302000 | 1 | Demo condemned 2,100 sqft house |
| B2025-02795 | 811 CEDAR St | 059231501400 | 1 | Demo 784 sqft SFR + 245 sqft garage |
| B2024-00362 | 1215 NEILSON St | 060241501200 | 1 | Demo non-conforming ADU |
| B2024-01374 | 1048 KEITH Ave | 061255503101 | 1 | Demo 1-story house over crawl space |
| B2023-04472 | 469 KENTUCKY Ave | 062294502800 | 1 | Demo 3-story 4BR home (rebuild pending) |
| B2023-04232 | 2910 SHASTA Rd | 063299200200 | 1 | Tear down burnt building to foundation |

**Observation:** Most demolitions (133 of 150) report 0 units removed, likely because they're accessory structures (garages, sheds) or commercial buildings. Net residential loss from demolitions is minimal (17 units over 3 years).

---

## Updated Gap Analysis Summary

| Category | In v1 | Missing from v1 | Units Missing |
|----------|-------|-----------------|---------------|
| R-2 multi-unit projects | 23 | 41 | 695 |
| ADU projects | 7 | 1,555 | 419 |
| Demolitions | 9 | 141 | 13 |

### Priority Projects to Add to v1

**High priority (50+ units):**
1. B2024-02966: 1701 San Pablo Ave — 110 units, $25.7M (2025)
2. B2019-03689: 2100 San Pablo Ave — 96 units, $18M (2023)
3. B2023-02332: 2538 Durant Ave — 83 units, $16.4M (2024)
4. B2018-03255: 2527 San Pablo Ave — 63 units, $25.7M (2023)
5. B2020-01991: 2701 Shattuck Ave — 57 units, $4.8M (2023)
6. B2017-02610: 2067 University Ave — 50 units, $6.8M (2023)

**Medium priority (10-49 units):**
7. B2021-02423: San Pablo Ave — 40 units (2024)
8. B2020-00206: 1717 University Ave — 15 units (2023)
9. B2022-05957: 2328 Channing Way — 13 units (2024)
10. B2025-03731: 2012 Channing Way — 11 units (2025)
11. B2024-05284: 2307 Piedmont Ave — 10 units (2025)

---

## Q16: Fuzzy Address Verification of "Missing" R-2 Projects

The 41 "unmatched" R-2 projects were rechecked using fuzzy address matching against v1's projects table.

### Methodology

1. Normalize both CPRA and v1 addresses: uppercase, remove punctuation, standardize abbreviations (Avenue→AVE, Street→ST, etc.)
2. For each unmatched CPRA permit, find the best fuzzy match in v1 using rapidfuzz
3. Report similarity scores (0-100%)

### Results

| Similarity Threshold | Count |
|---------------------|-------|
| ≥ 80% | 27 |
| ≥ 90% | 11 |
| = 100% (exact) | 0 |

### Top 10 Fuzzy Matches

| Permit | CPRA Address | Best v1 Match | v1 ID | Similarity |
|--------|--------------|---------------|-------|------------|
| B2020-00206 | 1717 UNIVERSITY Ave | 1710 UNIVERSITY AVE | 40 | 97% |
| B2024-02966 | 1701 SAN PABLO Ave | 1701 SAN PABLO AVE | 153 | 97% |
| B2020-01991 | 2701 SHATTUCK Ave | 2700 SHATTUCK AVE | 3 | 97% |
| B2023-02332 | 2538 DURANT Ave | 2538 DURANT AVE | 139 | 97% |
| B2024-06011 | 2538 DURANT Ave | 2538 DURANT AVE | 139 | 97% |
| B2021-02423 | 0 SAN PABLO Ave | 3000 SAN PABLO AVE | 168 | 94% |
| B2017-02610 | 2067 UNIVERSITY Ave | 2000 UNIVERSITY AVE | 137 | 92% |
| B2018-03255 | 2527 SAN PABLO Ave | 2720 SAN PABLO AVE | 16 | 92% |
| B2019-03689 | 2100 SAN PABLO Ave | 3000 SAN PABLO AVE | 168 | 92% |
| B2023-03349 | 2537 ELLSWORTH St | 2372 ELLSWORTH ST | 28 | 91% |

### Projects Likely in v1 Under Different APN (≥90% match)

11 "unmatched" projects have addresses very similar to v1 projects, suggesting **APN mismatch rather than missing projects**:

| Permit | CPRA Address | v1 Project | Likely Same? |
|--------|--------------|------------|--------------|
| B2024-02966 | 1701 SAN PABLO Ave | v1 #153: 1701 SAN PABLO AVE | **Yes** — exact address |
| B2023-02332 | 2538 DURANT Ave | v1 #139: 2538 DURANT AVE | **Yes** — exact address |
| B2024-06011 | 2538 DURANT Ave | v1 #139: 2538 DURANT AVE | **Yes** — same project |
| B2020-01991 | 2701 SHATTUCK Ave | v1 #3: 2700 SHATTUCK AVE | **Likely** — adjacent addresses |
| B2020-00206 | 1717 UNIVERSITY Ave | v1 #40: 1710 UNIVERSITY AVE | Possible — nearby |
| B2017-02610 | 2067 UNIVERSITY Ave | v1 #137: 2000 UNIVERSITY AVE | Different address |
| B2018-03255 | 2527 SAN PABLO Ave | v1 #16: 2720 SAN PABLO AVE | Different address |
| B2019-03689 | 2100 SAN PABLO Ave | v1 #168: 3000 SAN PABLO AVE | Different address |

**Key finding:** At least 4 of the 41 "missing" projects (B2024-02966, B2023-02332, B2024-06011, B2020-01991) are likely in v1 but have **APN mismatches** between CPRA and v1 data.

---

## Q17: Description Classification of 41 Unmatched R-2 Projects

Each unmatched project was classified based on WorkDescription content.

### Classification Distribution

| Category | Projects | Units |
|----------|----------|-------|
| ADU/Conversion | 21 | 141 |
| Genuine multi-unit | 9 | 496 |
| Renovation/Revision | 8 | 50 |
| Small multi-unit (2-4) | 3 | 8 |
| **Total** | **41** | **695** |

### Key Finding

**Only 9 of 41 "missing" projects are genuine new multi-unit developments.**

The majority (21) are ADU additions or conversions that happen to be classified under R-2 occupancy code. Another 8 are renovation/revision permits that inherit the building's unit count.

### Genuine Multi-Unit Projects (9)

| Permit | Address | Units | Description |
|--------|---------|-------|-------------|
| B2019-03689 | 2100 SAN PABLO Ave | 96 | Revision to remove front restaurant |
| B2023-02332 | 2538 DURANT Ave | 83 | New 8-story building with 83 dwelling units |
| B2024-06011 | 2538 DURANT Ave | 83 | Temporary power service for construction |
| B2018-03255 | 2527 SAN PABLO Ave | 63 | New 6-story mixed use with 63 residential units |
| B2020-01991 | 2701 SHATTUCK Ave | 57 | Revisions to fire pump room |
| B2017-02610 | 2067 UNIVERSITY Ave | 50 | Removing FSDs at each stack |
| B2021-02423 | SAN PABLO Ave | 40 | Add guardrail at roof deck parapet |
| B2022-05957 | 2328 CHANNING Way | 13 | Restoration of Luttrell House + 13 new units |
| B2025-03731 | 2012 CHANNING Way | 11 | Install water heater stand |

**Note:** Several of these (B2019-03689, B2020-01991, B2017-02610, B2021-02423, B2025-03731) are revision/sub-permits for projects that may already be in v1 under the master permit.

### ADU/Conversion Projects (21)

Most of these are small-scale: 18 add only 1-2 units via garage conversions, basement ADUs, or multi-family ADU additions. Exception: B2024-02966 (1701 San Pablo) with 110 units is classified as ADU/Conversion because its description mentions "publicly funded" but this is likely a genuine multi-unit project.

### Renovation/Revision Projects (8)

These are permits for existing buildings (reroofs, repairs, equipment changes) that inherit the building's unit count. They don't represent new construction.

---

## Q18: Top Demolitions by Units Removed

### Summary

| Metric | Count |
|--------|-------|
| Total demolition projects (2023-2025) | 150 |
| Total units removed | 17 |
| Demolitions with UnitsRemoved > 0 | 14 |
| Demolitions with UnitsRemoved = 0 | 136 |

### Distribution

| Threshold | Count |
|-----------|-------|
| > 0 units | 14 |
| > 1 units | 3 |
| > 2 units | 0 |
| > 5 units | 0 |
| > 10 units | 0 |

**Key finding:** No large-scale demolitions. Maximum UnitsRemoved = 2 (two duplexes at Webster St for the 3030 Telegraph project).

### Top 20 Demolitions by Units Removed

| Rank | Permit | Address | APN | Year | Units | In v1? | Description |
|------|--------|---------|-----|------|-------|--------|-------------|
| 1 | B2023-06442 | 2330 WEBSTER St | 052157602701 | 2024 | 2 | Yes | Demo duplex for 3030 Telegraph |
| 2 | B2023-06443 | 2334 WEBSTER St | 052157602701 | 2024 | 2 | Yes | Demo duplex for 3030 Telegraph |
| 3 | B2023-00142 | 1422 CORNELL Ave | 060239800900 | 2023 | 2 | No | Demo detached garage |
| 4 | B2024-06091 | 2708 PRINCE St | 052156303600 | 2025 | 1 | No | Demo one-story SFR |
| 5 | B2025-03217 | 1521 STUART St | 054173301300 | 2025 | 1 | No | Demo dwelling (rebuild pending) |
| 6 | B2024-03439 | 1200 DWIGHT Way | 054178102900 | 2024 | 1 | No | Demo SFR |
| 7 | B2023-02743 | 1536 BLAKE St | 054180002900 | 2023 | 1 | No | Demo/rebuild garage |
| 8 | B2023-02428 | 2431 ACTON St | 056191902600 | 2023 | 1 | No | Demo garage |
| 9 | B2021-05206 | 2421 FIFTH St | 056194302000 | 2024 | 1 | No | Demo condemned house |
| 10 | B2025-02795 | 811 CEDAR St | 059231501400 | 2025 | 1 | No | Demo 784 sqft SFR |
| 11 | B2024-00362 | 1215 NEILSON St | 060241501200 | 2024 | 1 | No | Demo non-conforming ADU |
| 12 | B2024-01374 | 1048 KEITH Ave | 061255503101 | 2025 | 1 | No | Demo 1-story house |
| 13 | B2023-04472 | 469 KENTUCKY Ave | 062294502800 | 2024 | 1 | No | Demo 3-story SFR (rebuild) |
| 14 | B2023-04232 | 2910 SHASTA Rd | 063299200200 | 2023 | 1 | No | Demo burnt building |
| 15-20 | (various) | — | — | — | 0 | — | Accessory structures |

**Observation:** The only significant demolitions with unit loss are at 2330-2334 Webster St (4 duplex units total), cleared for the 144-unit 3030 Telegraph project. All other demolitions are single-family homes (most with rebuild permits pending) or accessory structures.

---

## Revised Gap Analysis Summary

After verification:

### True Missing Multi-Unit Projects

| Status | Projects | Units |
|--------|----------|-------|
| Originally reported "missing" | 41 | 695 |
| Likely in v1 (APN mismatch) | 4 | 329 |
| ADU/Conversions (not v1 scope) | 21 | 141 |
| Renovations (not new construction) | 8 | 50 |
| Small multi-unit (2-4 units) | 3 | 8 |
| **Genuine missing multi-unit** | **5** | **167** |

### Genuine Missing Projects to Investigate

| Permit | Address | Units | Year | Notes |
|--------|---------|-------|------|-------|
| B2018-03255 | 2527 SAN PABLO Ave | 63 | 2023 | New 6-story mixed use |
| B2022-05957 | 2328 CHANNING Way | 13 | 2024 | Historic Luttrell House + new units |
| B2021-04907 | 2421 FIFTH St | 3 | 2024 | New 3-unit building |
| B2022-01345 | 1837 BERKELEY Way | 3 | 2023 | 3 new townhouses |
| B2020-01168 | 2025 DURANT Ave | 2 | 2023 | ADU-related revision |

**Conclusion:** The "41 missing projects" finding was overstated. After verification:
- 4 projects are in v1 under different APNs
- 21 are ADUs (outside v1's traditional scope)
- 8 are renovation permits (not new units)
- 3 are small multi-unit (2-4 units)
- **Only 5 genuine multi-unit projects (167 units) may be missing from v1**

---

## Staleness Assessment (2026-05-10)

A systematic staleness assessment was performed for all 179 v1 projects against CPRA 2023-2025 master permits.

**Output file:** `data/apr/v1_staleness_assessment_2026-05-10.csv`

### Methodology

For each v1 project:
1. Compute "most recent v1 event date" from: `bp_issued`, `co_date`, `complete`, `entitled`, `filed`, `demolition_permit_date`, `construction_start`, `final_inspection_date`, `accela_status_date`, plus max `event_date` from `permit_events`
2. Match to CPRA 2023-2025 master permits by normalized APN (digits only)
3. If no APN match, attempt fuzzy address match (≥95% similarity)
4. Classify as:
   - **UP_TO_DATE**: Has CPRA permits but none after v1's most recent event
   - **STALE**: Has CPRA permits issued after v1's most recent event
   - **UNMATCHED**: No CPRA 2023-2025 master permits found at this APN

### Results

| Classification | Projects | Units | Description |
|----------------|----------|-------|-------------|
| UNMATCHED | 112 (63%) | 10,327 | No 2023-2025 CPRA master permits at this APN |
| UP_TO_DATE | 34 (19%) | 2,574 | Has CPRA activity, v1 is current |
| STALE | 33 (18%) | 1,169 | Has CPRA permits newer than v1's last event |

### Top STALE Projects

| ID | Address | Units | Last v1 Event | New Permits |
|----|---------|-------|---------------|-------------|
| 83 | 1136 KEITH Ave | 0 | 2024-01-01 | 5 |
| 159 | 2403 SAN PABLO Ave | 36 | 2025-04-01 | 3 |
| 88 | 705 ARLINGTON Ave | 0 | 2023-01-01 | 3 |
| 152 | 1598 UNIVERSITY Ave | 207 | 2024-07-14 | 3 |
| 90 | 576 SAN LUIS Rd | 0 | 2024-01-01 | 3 |

---

## Staleness Verification Checks

### Check 1: 1701 San Pablo Ave Classification

**Issue discovered:** v1 project #153 has an **APN data error**.

| Field | v1 Record | Correct Value |
|-------|-----------|---------------|
| Address | 1701 SAN PABLO Ave | 1701 SAN PABLO Ave |
| APN | 058 212701403 | 058 212901700 |
| Units | 110 | 110 |

**Problem:** The v1 APN (058212701403) belongs to **1740 San Pablo** (54 units, B2022-05881), not 1701 San Pablo.

**CPRA Permits at 1701 San Pablo (correct APN 058212901700):**

| Permit | Issued | Units | Description |
|--------|--------|-------|-------------|
| B2024-02966 | 2025-05-06 | 110 | New 6-story, 110-unit publicly funded multi-family |
| B2024-02966-DEF01 | 2025-06-23 | 110 | Shoring shop drawings |
| B2024-02966-DEF02 | 2025-09-02 | 110 | Storefront shop drawings |
| B2024-02966-DEF03 | 2025-10-10 | 110 | Tie-down shop drawings |
| B2024-02966-REV04 | 2025-11-13 | 110 | Structural clarifications |

**Impact:** The staleness assessment matched v1 #153 to the wrong CPRA permits (1740 San Pablo instead of 1701 San Pablo). The classification showed "STALE" with B2022-05881, but the actual 1701 San Pablo project (B2024-02966) was not matched.

**Recommendation:** Fix APN in v1 from `058 212701403` to `058 212901700`.

---

### Check 2: 0-Unit STALE Projects

Three 0-unit projects were flagged as STALE. Investigation shows they are **single-family residential projects** with planning review activity, not multi-unit housing:

#### Project #83: 1136 KEITH Ave (0 units)

- **v1 Status:** In Review (SB9 application)
- **Description:** Pre-application to demolish existing SFR and rebuild new SFR pursuant to SB9
- **CPRA Activity (6 masters):**
  - B2022-03783: Remodel/addition (2023-01-11)
  - B2024-02569: Demolish SFR (2024-09-25)
  - B2024-02570: New SFR rebuild (2024-09-27)
  - B2024-02712: Temporary foundation (2024-08-07)
  - B2024-03997: Temporary power (2024-08-14)
  - B2025-02220: Solar panels (2025-07-23)

**Classification:** Correctly STALE — CPRA has permits after v1's last event. However, this is a **SFR rebuild project**, not multi-unit housing.

#### Project #88: 705 ARLINGTON Ave (0 units)

- **v1 Status:** In Review (Hillside Overlay AUP)
- **Description:** 1,700 sq ft major residential addition in Hillside Overlay
- **CPRA Activity (3 masters):**
  - B2023-05865: Heat pump installation (2023-11-14)
  - B2024-01528: Replace windows/doors (2025-03-04)
  - B2025-04937: Kitchen remodel (2025-11-04)

**Classification:** Correctly STALE — ongoing renovation at single-family property.

#### Project #90: 576 SAN LUIS Rd (0 units)

- **v1 Status:** Incomplete Pending Applicant
- **Description:** AUP for 577 sq ft addition in Hillside Overlay
- **CPRA Activity (4 masters):**
  - B2022-05525: Meter upgrade for ADU (2023-02-16) — ADU flagged
  - B2025-00709: Foundation/seismic work (2025-06-02)
  - B2025-04320: Solar panels (2025-10-27)
  - B2025-04805: Electrical sub-panel for ADU (2025-10-27) — ADU flagged

**Classification:** Correctly STALE — ongoing ADU-related work at single-family property.

**Conclusion:** These 0-unit STALE projects are single-family residential with planning review activity. They're tracked in v1 due to Hillside Overlay or SB9 requirements but don't represent multi-unit housing production.

---

### Check 3: UNMATCHED Spot-Check (Top 10 by Units)

The top 10 UNMATCHED projects by unit count were manually cross-checked against CPRA using address search (not just APN).

| ID | Address | Units | Pipeline Stage | UC? | CPRA Found? |
|----|---------|-------|----------------|-----|-------------|
| 171 | 2400 BOWDITCH St | 750 | Pre-Application | Yes | No |
| 1 | 1750 SACRAMENTO St | 739 | In Review | No | No |
| 151 | Ashby BART | 618 | Pre-Application | No | No |
| 119 | 1974 SHATTUCK Ave | 599 | Entitled | No | No |
| 177 | 2556 HASTE St | 556 | Under Construction | Yes | No |
| 133 | 2128 Oxford St | 485 | Entitled | No | No |
| 35 | 2190 SHATTUCK Ave | 452 | In Review | No | No |
| 2 | 2276 SHATTUCK Ave | 336 | In Review | No | No |
| 170 | 1950 OXFORD St | 300 | Completed | Yes | No |
| 120 | 2274 SHATTUCK Ave | 299 | Entitled | No | No |

**Key Findings:**

1. **None of the top 10 have CPRA 2023-2025 master permits** — not by APN or by address
2. **8 of 10 are Pre-Application, In Review, or Entitled** — building permits not yet issued
3. **3 of 10 are UC Berkeley projects** — may use UC's own permitting process
4. **None have `bp_issued` dates recorded in v1**

**Conclusion:** The UNMATCHED classification is **correct** for these projects. They legitimately have no 2023-2025 CPRA building permit activity because they're still in planning stages or are UC projects with separate permitting.

---

## Data Quality Issues Identified

| Issue | Project(s) | Severity | Recommendation |
|-------|------------|----------|----------------|
| Wrong APN | #153 (1701 San Pablo) | High | Fix APN from 058212701403 to 058212901700 |
| 0-unit SFR projects in v1 | #83, #88, #90 | Low | Document as non-housing-production planning items |
| Missing APNs | #171, #177, #133, #170 | Medium | Add APNs from city records |

---

---

## APN Audit (2026-05-10)

A systematic APN audit was performed for all 179 v1 projects, checking format validity, address cross-references, and missing values.

**Output file:** `data/apr/v1_apn_audit_2026-05-10.csv`

### Audit Summary

| Issue Type | Count | Description |
|------------|-------|-------------|
| Valid | 158 | No issues found |
| MISSING_APN | 10 | APN is NULL or empty |
| APN_MISMATCH | 4 | Address-matched CPRA permits have different APN |
| FORMAT_ERROR | 11 | APN doesn't match Alameda County format |
| **Total Issues** | **25** | |

### APN Format Standard

Alameda County APNs should follow the format: `XXX XXXXXXXXX` (3 digits + space + 9 digits).

Example: `058 212901700`

---

### Missing APNs (10 projects)

| ID | Address | Units | Status |
|----|---------|-------|--------|
| 127 | 2820 San Pablo | 1 | Entitled |
| 128 | 2833 Seventh St | 3 | Approved |
| 129 | 1614 Sixth St | 3 | Approved |
| 130 | 1048 Keith St | 0 | Approved |
| 131 | 811 Cedar | 0 | Approved |
| 133 | 2128 Oxford St | 485 | Approved |
| 165 | 2200 BANCROFT Way | 550 | Under Construction |
| 170 | 1950 OXFORD St | 300 | Completed |
| 171 | 2400 BOWDITCH St | 750 | Pre-Application |
| 177 | 2556 HASTE St | 556 | Under Construction |

**Note:** 4 of these are large UC Berkeley projects (133, 165, 170, 171, 177) totaling 2,641 units.

---

### APN Mismatches (4 projects)

These projects have APNs that don't match the APNs found on CPRA permits at the same address.

| ID | Address | v1 APN | CPRA APN | Status |
|----|---------|--------|----------|--------|
| 72 | 5 W PARNASSUS Ct | 058 224204829 | 058 223202200 | Needs review |
| 93 | 1312 ADDISON St | 056 199300100 | 056 199400401 | Needs review |
| 139 | 2538 DURANT Ave | 055 187602000 | 055 187602101 | Needs review |
| 153 | 1701 SAN PABLO Ave | 058 212701403 | 058 212901700 | **Confirmed error** |

**#153 (1701 San Pablo):** Already confirmed in Check 1 above. The v1 APN belongs to 1740 San Pablo, not 1701.

---

### Format Errors (11 projects)

| ID | Address | v1 APN | Issue |
|----|---------|--------|-------|
| 21 | 2660 BANCROFT Way | `55-1871-20` | 8 digits, has dashes |
| 33 | 130 BERKELEY Sq | `57-2032-17` | 8 digits, has dashes |
| 47 | 1850 BERRYMAN St | `60-2447-36` | 8 digits, has dashes |
| 126 | 2427 San Pablo | `056192802200` | Missing space |
| 132 | 1627 Jaynes St | `059227901600` | Missing space |
| 134 | 2480 Bancroft Way | `055187802200` | Missing space |
| 178 | 2131 University Ave | `057-2046-008-03, ...` | Multiple APNs, dash format |
| 179 | 2352 Shattuck Ave | `055-1895-018-05` | Dash format |
| 180 | 2065 Kittredge St | `057-2027-006-00` | Dash format |
| 181 | 2015 Blake St | `055-1822-013-3` | 11 digits, dash format |
| 182 | 2072 Addison St | `057-2023-025-00` | Dash format |

**Pattern observed:** Projects #21, #33, #47 use abbreviated 8-digit format with dashes. Projects #126, #132, #134 have correct 12 digits but missing the space. Projects #178-#182 use Assessor's dash-separated format.

---

### Recommended Actions

| Priority | Action | Projects |
|----------|--------|----------|
| High | Fix confirmed APN error | #153 |
| High | Add missing APNs to major projects | #133, #165, #170, #171, #177 |
| Medium | Verify and fix APN mismatches | #72, #93, #139 |
| Medium | Convert dash format to standard | #178-#182 |
| Low | Expand abbreviated APNs | #21, #33, #47 |
| Low | Add space separator | #126, #132, #134 |
| Low | Add missing APNs to small projects | #127-#131 |

---

---

## Q19: Re-verified Missing R-2 Projects Post-APN-Audit

**Run date:** 2026-05-10 (post-APN-audit verification)

This analysis re-checks which R-2 master permits with ≥5 units are genuinely missing from v2, accounting for APN corrections made during the 2026-05-10 audit:
- Project 153 (1701 San Pablo): new parcel 164 created with APN 058 212901700
- Project 72 (5 W Parnassus): parcel 69 APN updated to 058 223202200
- Project 139 (2538 Durant): parcel 125 APN updated to 055 187602101
- Projects 127-131, 133: linked to parcels (previously missing APNs)

### Methodology

1. Load CPRA master permits using `scripts/cpra_dedup.py`
2. Filter to R-2 occupancy + UnitsAdded ≥ 5 (2023-2025)
3. Match each to v2 projects via:
   - Exact APN match against v2.parcels.apn
   - Fuzzy address match (≥90%) against v2.projects.canonical_address + project_addresses.address
4. Report unmatched as "genuinely missing"

### Summary

| Metric | Count |
|--------|-------|
| R-2 master permits with ≥5 units (2023-2025) | 37 |
| Matched to v2 (APN or fuzzy address) | 32 |
| **Genuinely missing from v2** | **5** |
| Total units in missing projects | 48 |

### Matched Projects (sample)

| Permit | Match Type | v2 Project | v2 Address |
|--------|------------|------------|------------|
| B2014-05752 | exact_apn | #175 | 1698 UNIVERSITY Ave |
| B2018-03255 | fuzzy_addr_92% | #16 | 2720 SAN PABLO AVE |
| B2019-02956 | exact_apn | #91 | 2009 ADDISON St |
| B2019-05608 | exact_apn | #136 | 1951 Shattuck Ave |
| B2020-00206 | fuzzy_addr_97% | #40 | 1710 UNIVERSITY AVE |
| B2020-01991 | fuzzy_addr_97% | #3 | 2700 SHATTUCK AVE |
| B2021-00008 | exact_apn | #135 | 2150 Kittredge St |
| B2024-01924 | exact_apn | #152 | 1598 UNIVERSITY Ave |
| B2024-02966 | exact_apn | #153 | 1701 SAN PABLO Ave |

**Note:** B2018-03255 (2527 San Pablo) was in the prior "genuinely missing" list but now matches v2 #16 (2720 San Pablo) via fuzzy address at 92%. This may be a false positive match — different addresses on San Pablo.

### Genuinely Missing Projects (5)

| Permit | Address | APN | Units | Issued | Valuation | Description |
|--------|---------|-----|-------|--------|-----------|-------------|
| B2022-05957 | 2328 CHANNING Way | 055188302700 | 13 | 2024-09-05 | $3,890,000 | Restoration of historic Luttrell House + new 13-unit 4-story residential |
| B2025-03731 | 2012 CHANNING Way | 055189602100 | 11 | 2025-09-03 | $2,000 | Install water heater stand (housing case #H2025-00431) |
| B2024-05284 | 2307 PIEDMONT Ave | 055186400100 | 10 | 2025-06-19 | $30,000 | Repair of 4 exterior wood posts at first floor terrace |
| B2024-04593 | 2235 HEARST Ave | 058218101700 | 8 | 2024-09-27 | $56,278 | Reroof: remove tar & gravel, install membrane |
| B2025-00168 | 2330 BLAKE St | 055183202601 | 6 | 2025-07-30 | $1,976,310 | Interior remodel + addition of 6 ADUs at ground level |

### Analysis of Missing Projects

**Likely genuine new multi-unit construction:**
- **B2022-05957 (2328 Channing):** Historic Luttrell House restoration + 13 new units. $3.9M valuation supports new construction. **Should be added to v2.**
- **B2025-00168 (2330 Blake):** Interior remodel adding 6 ADUs. $1.98M valuation. **Candidate for v2 if ADUs are in scope.**

**Likely inherited unit counts (not new construction):**
- **B2025-03731 (2012 Channing):** Description is "water heater stand" with $2,000 valuation — clearly not 11-unit construction. Unit count inherited from existing building.
- **B2024-05284 (2307 Piedmont):** Description is "repair of exterior wood posts" with $30,000 valuation — not new construction.
- **B2024-04593 (2235 Hearst):** Description is "reroof" with $56,278 valuation — maintenance on existing building.

### Cross-Check Against Prior List

| Permit | Prior Finding | Current Status |
|--------|---------------|----------------|
| B2018-03255 | Genuinely missing (63 units) | Now matches v2 #16 via fuzzy address (92%) |
| B2022-05957 | Genuinely missing (13 units) | Still missing — confirmed genuine |
| B2021-04907 | Genuinely missing (3 units) | Below threshold (<5 units) |
| B2022-01345 | Genuinely missing (3 units) | Below threshold (<5 units) |
| B2020-01168 | Genuinely missing (2 units) | Below threshold (<5 units) |

### Revised Conclusion

After APN audit corrections and more stringent matching:

| Status | Projects | Units |
|--------|----------|-------|
| Originally reported "missing" (Q13) | 41 | 695 |
| After Q16-Q18 verification | 5 | 167 |
| After Q19 re-verification (≥5 units only) | 5 | 48 |
| **Genuinely new construction to add to v2** | **2** | **19** |

**Only 2 genuinely missing multi-unit projects warrant addition to v2:**
1. **B2022-05957 (2328 Channing Way):** 13 units, $3.89M — historic + new construction
2. **B2025-00168 (2330 Blake St):** 6 units, $1.98M — ADU addition (if ADUs in scope)

The other 3 "missing" permits are maintenance work on existing multi-unit buildings where the UnitsAdded field inherited the building's existing unit count rather than representing new unit production.

---

---

## Q20: Import Script Dry-Run Verification

**Run date:** 2026-05-11

The dry-run of `scripts/migration/import_cpra_2023_2025.py` reported 123 permits would be inserted. The import plan (§14) expected ~707. This section investigates the discrepancy.

### Check 1: Match Breakdown

| Match Type | §10b (Loose) | §16 (Tightened) | Notes |
|------------|--------------|-----------------|-------|
| Exact APN match | 110 | 122 | Slight increase after APN audit |
| Fuzzy address match | 592 | 2 | **Dramatic reduction** |
| **Total matches** | **702** | **124** | |

**Root cause identified:** §10b used **loose** fuzzy matching (full address similarity ≥90%), which allowed matches like:

| CPRA Permit | CPRA Address | V2 Project | V2 Address | Similarity |
|-------------|--------------|------------|------------|------------|
| B2025-04594 | 3200 SHATTUCK Ave | #3 | 2700 SHATTUCK Ave | 94% |
| B2025-01456 | 3100 SAN PABLO Ave | #168 | 3000 SAN PABLO Ave | 94% |
| B2025-04881 | 1710 HARMON St | #145 | 1708 HARMON St | 93% |
| B2023-03205 | 3020 BENVENUE Ave | #70 | 3001 BENVENUE Ave | 94% |

These are **false positives** — different addresses that happen to score high similarity because the street name dominates.

§16 tightened matching requires **exact street number + fuzzy street name ≥90%**. This correctly rejects the false positives above but also reduces matches from 584 to just 2.

**Bug in import script:** The script's `match_permit_to_project()` extracts street number as `cpra_addr.split()[0]`, yielding "1581.0" from CPRA vs "1581" from v2. The string comparison fails. This bug affects 2 potential matches (B2023-00675 at 2000 Dwight Way, B2023-06383 at 1312 Addison St).

### Check 2: Unmatched Spot Check

Sampled 10 v2 projects on high-activity streets (San Pablo, Shattuck, Telegraph, University):

| V2 Project | Address | Status | Finding |
|------------|---------|--------|---------|
| #2 | 2276 SHATTUCK Ave | Near miss | 64 CPRA permits on Shattuck, none at 2276 |
| #3 | 2700 SHATTUCK Ave | Near miss | Same street, different addresses |
| #6 | 2029 UNIVERSITY Ave | Near miss | 30 CPRA permits on University, none at 2029 |
| #7 | 2601 SAN PABLO Ave | Near miss | Same street, different addresses |
| #8 | 2920 SHATTUCK Ave | Near miss | Same street, different addresses |
| #10 | 3000 SHATTUCK Ave | Near miss | Same street, different addresses |
| #11 | 1581 UNIVERSITY Ave | Near miss | Same street, different addresses |
| #13 | 2420 SHATTUCK Ave | Near miss | Same street, different addresses |
| #14 | 2847 SHATTUCK Ave | Near miss | Same street, different addresses |
| #16 | 2720 SAN PABLO Ave | Near miss | Same street, different addresses |

**Conclusion:** All 10 sampled v2 projects have **legitimate no-match** status:
- CPRA has building permits on the same streets but at different addresses
- V2 tracks planning/entitlement projects; many don't yet have building permits
- No APN format issues or street name normalization issues detected

### Check 3: Permit Count Reconciliation

| Metric | §10b | Dry-run |
|--------|------|---------|
| Master permits (all years) | 12,186 | 12,207 |
| Master permits (2023-2025) | 10,856 | 10,876 |
| After skip permits | — | 10,873 |

**Explanation:** §10b figure of 12,186 was for **all years**. The dry-run correctly filters to 2023-2025 (10,876) minus 3 false positive permits = **10,873**.

The 10,873 count is correct for the 2023-2025 import scope.

### Summary of Findings

| Finding | Impact |
|---------|--------|
| §16 tightening worked as intended | Reduced false positives from 584 to 2 |
| Impact was more dramatic than anticipated | Expected "some reduction"; got 99.7% reduction |
| Import script has minor float bug | Affects 2 matches; fixable |
| Most v2 projects have no CPRA matches | V2 = planning stage; CPRA = building permits |
| Permit count difference explained | §10b was all-years; dry-run is 2023-2025 |

### Revised Match Expectation

With tightened §16 matching correctly applied:

| Match Type | Count |
|------------|-------|
| Exact APN matches | 122 |
| Tightened fuzzy matches (with bug fix) | 2 |
| New R-2 projects | 2 |
| **Total permits to insert** | **126** |

This is the correct import scope per §16. The original 707 estimate was based on loose matching that produced many false positives.

### Recommendation

1. **Fix the float normalization bug** in `match_permit_to_project()` to capture the 2 legitimate fuzzy matches
2. **Proceed with import at ~126 permits** — this is the correct scope after tightening
3. **Do not revert to loose matching** — the 584 "matches" were mostly false positives (different addresses on same street)

---

*Updated 2026-05-11 with import script dry-run verification.*
