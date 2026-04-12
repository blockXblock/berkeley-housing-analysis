# Berkeley 2024 APR Comparison Report

**Generated:** 2026-03-21
**Data Sources:**
- City's Official HCD Submission: [CA Open Data Portal - Table A](https://data.ca.gov/dataset/housing-element-annual-progress-report-apr-data-by-jurisdiction-and-year)
- Our Draft: `data/apr/draft_2024_table_a.csv`

---

## Executive Summary

| Metric | Our Draft | City Submission | Difference |
|--------|-----------|-----------------|------------|
| Total Projects | 39 | 39 | 0 |
| Total Proposed Units | 3,508 | 3,832 | -324 |
| VLI Units (DR) | 88 | 497 | **-409** |
| LI Units (DR) | 35 | 136 | **-101** |
| MOD Units (DR) | 41 | 37 | +4 |
| Approved Projects | 5 | 12 | -7 |
| Pending Projects | 34 | 27 | +7 |

**Key Finding:** Our income extraction captured only 18% of the VLI units and 26% of the LI units reported by the city. This suggests the city has access to more detailed affordability data than is available in the permit descriptions.

---

## Table A: Applications Submitted

### City's 2024 Submission Summary

| Category | Value |
|----------|-------|
| Total rows | 39 |
| Total proposed units | 3,832 |
| VLI (deed-restricted) | 497 |
| VLI (non-deed-restricted) | 23 |
| LI (deed-restricted) | 136 |
| MOD (deed-restricted) | 37 |
| Above Moderate | 3,139 |
| Approved | 12 |
| Pending | 27 |

### Projects in OUR Draft That CITY Missed (15 projects)

These projects appear in our `housing_projects_FINAL.csv` with year=2024 but are NOT in the city's HCD submission:

| Address | APN | Units | Notes |
|---------|-----|-------|-------|
| 1312 ADDISON St | 056 199300100 | 0 | Non-housing use permit |
| 1899 OXFORD St | 058 218101905 | 212 | **Major project missing!** |
| 1939 MARIN Ave | 061 257401300 | 1 | ADU |
| 2009 ADDISON St | 057 202502300 | 0 | Hotel use modification |
| 2029 UNIVERSITY Ave | 057 205300801 | 240 | **Major project missing!** |
| 2115 KITTREDGE St | 057 203000900 | 148 | **Major project missing!** |
| 2276 SHATTUCK Ave | 057 202800400 | 336 | **Major project missing!** |
| 2326 DURANT Ave | 055 188401600 | 70 | Pre-application |
| 2328 GRANT St | 055 190501200 | 1 | ADU |
| 2372 ELLSWORTH St | 055 188700300 | 63 | SB-330 project |
| 2420 ASHBY Ave | 052 157307802 | 4 | Conversion |
| 2428 MILVIA St | 055 189800100 | 8 | Landmarked building relocation |
| 2614 TELEGRAPH Ave | 055 183600800 | 31 | SB-330 project |
| 2955 SHATTUCK Ave | 053 158901801 | 74 | Density Bonus |
| 576 SAN LUIS Rd | 062 291602800 | 0 | Hillside addition |

**Total missing from city: 1,168 units** (including major projects at Oxford, University, Kittredge, and Shattuck)

### Projects in CITY's Report That WE'RE Missing (18 projects)

These projects appear in the city's HCD submission but NOT in our `housing_projects_FINAL.csv`:

| Address | APN | Units | Notes |
|---------|-----|-------|-------|
| 0 PARKER St | 055 182901100 | 1 | |
| 811 CEDAR St | 059 231501400 | 1 | |
| 1048 KEITH Ave | 061 255503101 | 1 | |
| 1614 SIXTH St | 057 211700401 | 2 | |
| 1627 JAYNES St | 059 227901600 | 1 | |
| 1974 SHATTUCK Ave | 057 205300200 | 599 | **Major project!** |
| 2037 DURANT Ave | 055 189400200 | 74 | |
| 2100 MILVIA St | 057 202201701 | 201 | **Major project!** |
| 2109 MILVIA St | 057 202301601 | 105 | |
| 2274 SHATTUCK Ave | 057 202800300 | 227 | **Major project!** |
| 2427 SAN PABLO Ave | 056 192802200 | 8 | |
| 2442 HASTE St | 055 188101800 | 36 | |
| 2462 BANCROFT Way | 055 187802000 | 66 | |
| 2530 BANCROFT Way | 055 187701601 | 110 | |
| 2680 BANCROFT Way | 055 187100103 | 79 | |
| 2733 SAN PABLO Ave | 054 174203200 | 152 | |
| 2820 SAN PABLO Ave | 053 166101100 | 1 | |
| 2833 SEVENTH St | 053 165803500 | 1 | |

**Total we're missing: 1,665 units** (including major projects at Shattuck, Milvia, Bancroft)

---

## Matching Projects With Discrepancies (19 projects)

### Unit Count Discrepancies

| Address | Our Units | City Units | Diff |
|---------|-----------|------------|------|
| 1136 KEITH Ave | 0 | 1 | -1 |
| 2036 BANCROFT Way | 85 | 87 | -2 |
| 2138 KITTREDGE St | 63 | 66 | -3 |
| 2145 GRANT St | 0 | 1 | -1 |
| 2147 SAN PABLO Ave | 15 | 16 | -1 |
| 2317 CHANNING Way | 22 | 5 | +17 |
| 2425 DURANT Ave | 250 | 169 | +81 |
| 2720 SAN PABLO Ave | 113 | 117 | -4 |
| 2847 SHATTUCK Ave | 132 | 136 | -4 |
| 3035 COLBY St | 0 | 2 | -2 |
| 3036 REGENT St | 0 | 1 | -1 |

### Income Category Discrepancies (Major)

| Address | Category | Our Value | City Value |
|---------|----------|-----------|------------|
| 1581 UNIVERSITY Ave | VLI | 0 | 14 |
| 1581 UNIVERSITY Ave | MOD | 0 | 9 |
| 1750 SACRAMENTO St | VLI | 0 | **248** |
| 1750 SACRAMENTO St | LI | 0 | **133** |
| 2109 VIRGINIA St | VLI | 0 | 11 |
| 2109 VIRGINIA St | MOD | 0 | 9 |
| 2147 SAN PABLO Ave | VLI | 0 | 3 |
| 2298 DURANT Ave | VLI | 0 | 5 |
| 2425 DURANT Ave | VLI | 0 | 13 |
| 2450 SHATTUCK Ave | VLI | 0 | 8 |
| 2720 SAN PABLO Ave | VLI | 0 | 10 |
| 2720 SAN PABLO Ave | MOD | 0 | 6 |
| 2847 SHATTUCK Ave | VLI | 0 | 13 |

**Note:** The 1750 SACRAMENTO St (North Berkeley BART) project has 248 VLI + 133 LI = 381 affordable units that our extraction missed. The description mentions "over 50% of the homes at affordable rent levels" but doesn't specify exact counts.

### Status Discrepancies

| Address | Our Status | City Status |
|---------|------------|-------------|
| 1136 KEITH Ave | Pending | Approved |
| 1750 SACRAMENTO St | Pending | **Approved** |
| 2109 VIRGINIA St | Approved | Pending |
| 2138 KITTREDGE St | Approved | Pending |
| 2201 BLAKE St | Approved | Pending |
| 2317 CHANNING Way | Pending | Approved |
| 3035 COLBY St | Approved | Pending |

---

## Table A2: RHNA Progress (Permits & Completions)

### Berkeley 2024 Building Activity Summary

| Stage | VLI | LI | MOD | Above Mod | Total |
|-------|-----|----|----|-----------|-------|
| Entitled | 351 | 135 | 1 | 1,458 | **1,945** |
| Building Permits | 47 | 4 | 0 | 588 | **639** |
| Certificates of Occupancy | 30 | 25 | 0 | 571 | **626** |

### Major Projects With Building Permits in 2024

| Address | Units | BP Date | Notes |
|---------|-------|---------|-------|
| 1598 University Ave | 207 | 2024-12-16 | |
| 3030 TELEGRAPH Ave | 144 | 2024-10-15 | |
| 2538 DURANT Ave | 83 | 2024-09-24 | |
| 1752 Shattuck Ave | 74 | 2024-06-13 | |
| 2137 Dwight Way | 67 | 2024-10-24 | |
| 2555 College Ave | 12 | 2024-04-26 | |

### Major Projects With Certificates of Occupancy in 2024

| Address | Units | CO Date | Notes |
|---------|-------|---------|-------|
| 2150 KITTREDGE St | 169 | 2024-03-20 | **Completed!** |
| 1951 SHATTUCK Ave | 163 | 2024-10-24 | **Completed!** |
| 2000 UNIVERSITY Ave | 82 | 2024-04-09 | **Completed!** |
| 2099 M L KING JR Way | 72 | 2024-05-17 | **Completed!** |
| 2527 SAN PABLO Ave | 63 | 2024-04-30 | **Completed!** |
| 2701 Shattuck Ave | 57 | 2024-07-18 | **Completed!** |

**Total 2024 Completions: 626 units** (30 VLI, 25 LI, 571 Above Moderate)

---

## Recommendations

### Data Quality Improvements

1. **Obtain affordability data directly from Planning**
   - Our description-based extraction missed 409 VLI units
   - City clearly has access to more precise affordability data
   - Request density bonus covenant data

2. **Reconcile project lists**
   - 15 projects in our data not in city submission
   - 18 projects in city submission not in our data
   - Major projects differ (likely different reporting periods or application dates)

3. **Update status tracking**
   - 7 status discrepancies found
   - Our statuses may be more current than city's APR snapshot

### Data Sources to Add

1. **For Table A (Applications):**
   - Application submission dates (APP_SUBMIT_DT currently empty)
   - Precise affordability unit counts from density bonus applications

2. **For Table A2 (RHNA Progress):**
   - Building permit issuance dates
   - Certificate of occupancy dates
   - Track entitled → permitted → completed pipeline

---

## Source Files

- City Table A: Downloaded from [CA Open Data Portal](https://data.ca.gov/dataset/housing-element-annual-progress-report-apr-data-by-jurisdiction-and-year)
- City Table A2: Same source
- Our Draft: `data/apr/draft_2024_table_a.csv`
- Status Mapping: `data/reference/apr_status_mapping.json`
- Income Extraction: `data/processed/income_extraction_audit.csv`
