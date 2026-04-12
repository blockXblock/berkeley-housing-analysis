# Missing Projects Diagnosis

**Generated:** 2026-03-21
**Purpose:** Diagnose why 14 projects in Berkeley's 2024 APR submission are missing from our `housing_projects_FINAL.csv`

---

## Executive Summary

| Category | Count | Units |
|----------|-------|-------|
| **(e) Scraping Gap** - Never collected from Accela | 13 | 1,263 |
| **(b) Permit Number Mismatch** - Different permit in our data | 1 | 1 |
| **Total Missing** | 14 | 1,264 |

**Root Cause:** Our Accela data collection has gaps in ZP2023 and ZP2024 permit coverage. We have 11 ZP2023 permits but are missing 6 that the city reported. Similarly, we have 28 ZP2024 permits but are missing 6.

---

## Detailed Project Analysis

### Category (e): Scraping Gaps - Need to Collect from Accela

These 13 projects are **completely absent** from all our databases and CSV files:

| # | Address | Permit | Units | App Date | Reason |
|---|---------|--------|-------|----------|--------|
| 1 | **1974 SHATTUCK Ave** | ZP2023-0040 | **599** | 2024-04-11 | Major project - never scraped |
| 2 | **2274 SHATTUCK Ave** | ZP2023-0079 | **227** | 2024-01-04 | Major project - never scraped |
| 3 | **2100 MILVIA St** | ZP2023-0163 | **201** | 2024-05-17 | Major project - never scraped |
| 4 | **2530 BANCROFT Way** | ZP2023-0126 | **110** | 2024-03-12 | Major project - never scraped |
| 5 | **2037 DURANT Ave** | ZP2023-0064 | **74** | 2024-03-29 | Never scraped |
| 6 | **2442 HASTE St** | ZP2024-0070 | **36** | 2024-10-08 | Never scraped |
| 7 | 2427 SAN PABLO Ave | ZP2022-0115 | 8 | 2024-12-06 | Small project - never scraped |
| 8 | 1614 SIXTH St | ZP2024-0008 | 2 | 2024-02-22 | Small project - never scraped |
| 9 | 2820 SAN PABLO Ave | ZP2022-0038 | 1 | 2024-12-06 | ADU - never scraped |
| 10 | 2833 SEVENTH St | ZP2023-0123 | 1 | 2024-02-26 | ADU - never scraped |
| 11 | 1048 KEITH Ave | ZP2024-0014 | 1 | 2024-02-29 | ADU - never scraped |
| 12 | 811 CEDAR St | ZP2024-0116 | 1 | 2024-12-19 | ADU - never scraped |
| 13 | 1627 JAYNES St | ZP2024-0129 | 1 | 2024-10-18 | ADU - never scraped |

**Total: 1,263 units** (including 1,211 in major projects of 74+ units)

### Category (b): Permit Number Mismatch

| # | Address | City's Permit | Our Permit | Units | Issue |
|---|---------|---------------|------------|-------|-------|
| 1 | 0 PARKER St | ZP2024-0100 | ZP2022-0063 | 1 | Same address, different permit |

**Details:** Our data shows 0 PARKER St with permit ZP2022-0063 (year 2022), status "Incomplete Pending Applicant", but the city reported it with ZP2024-0100 in their 2024 APR. This appears to be a follow-up permit for the same property.

---

## Permit Coverage Analysis

### ZP2023 Permits

| Status | Permits |
|--------|---------|
| We have | ZP2023-0008, 0058, 0063, 0070, 0089, 0090, 0095, 0096, 0099, 0107, 0155 (11 total) |
| We're missing | ZP2023-0040, 0064, 0079, 0123, 0126, 0163 (6 total) |
| Gap rate | 35% of city's ZP2023 permits are missing from our data |

### ZP2024 Permits

| Status | Permits |
|--------|---------|
| We have | 28 unique ZP2024 permits |
| We're missing | ZP2024-0008, 0014, 0070, 0100, 0116, 0129 (6 total) |
| Gap rate | 18% of city's ZP2024 permits are missing from our data |

---

## Impact Analysis

### By Unit Count

| Category | Missing Units | % of City's Total |
|----------|---------------|-------------------|
| Major (100+ units) | 1,137 | 30% |
| Medium (10-99 units) | 118 | 3% |
| Small (1-9 units) | 9 | <1% |
| **Total** | **1,264** | **33%** |

### Affordable Units Missed

| Income Level | Units Missed |
|--------------|--------------|
| VLI | 114 |
| LI | 3 |
| MOD | 0 |
| Above Moderate | 1,147 |

The 4 major projects we missed (1974 Shattuck, 2274 Shattuck, 2100 Milvia, 2530 Bancroft) account for 114 of the 409 VLI units we undercounted.

---

## Recommended Actions

### Immediate: Scrape Missing Permits

Run `accela_workflow.py generate` for these permit numbers, then `parse` and `save`:

```bash
# Priority 1: Major projects (1,000+ total units)
ZP2023-0040  # 1974 Shattuck - 599 units!
ZP2023-0079  # 2274 Shattuck - 227 units
ZP2023-0163  # 2100 Milvia - 201 units
ZP2023-0126  # 2530 Bancroft - 110 units
ZP2023-0064  # 2037 Durant - 74 units
ZP2024-0070  # 2442 Haste - 36 units

# Priority 2: Small/ADU projects
ZP2022-0115  # 2427 San Pablo - 8 units
ZP2024-0008  # 1614 Sixth - 2 units
ZP2022-0038  # 2820 San Pablo - 1 unit
ZP2023-0123  # 2833 Seventh - 1 unit
ZP2024-0014  # 1048 Keith - 1 unit
ZP2024-0116  # 811 Cedar - 1 unit
ZP2024-0129  # 1627 Jaynes - 1 unit
```

### Systematic: Improve Scraping Coverage

1. **Compare permit number sequences** - Identify gaps between our lowest and highest permit numbers per year
2. **Scrape all "ZP" permits** from Accela's active permits list periodically
3. **Cross-reference city APR** annually to catch any we missed

### Data Pipeline Fix

For the permit mismatch case (0 PARKER St), update the data pipeline to:
1. Track multiple permits per address
2. Link related permits (amendments, modifications) to base project
3. Use the most recent permit for APR reporting

---

## Files Generated

- `data/reference/city_apr_2024_table_a.csv` - City's official 2024 submission
- `data/apr/missing_projects_diagnosis.md` - This file

## Data Sources Searched

| Database/File | Tables Searched | Missing Found |
|---------------|-----------------|---------------|
| databases/berkeley.db | zoning_projects_with_parcels | 0 |
| databases/accela_reports.db | active_zoning_classified, record_details | 1 (mismatch) |
| databases/berkeley_housing_analysis.db | projects, project_permits | 1 (mismatch) |
| databases/berkeley_address_centric.db | projects | 1 (mismatch) |
| data/processed/*.csv | All 43 files | 0 |
| outputs/*.csv | All files | 0 |

---

## Appendix: Permit Numbers to Scrape

```
ZP2022-0038
ZP2022-0115
ZP2023-0040
ZP2023-0064
ZP2023-0079
ZP2023-0123
ZP2023-0126
ZP2023-0163
ZP2024-0008
ZP2024-0014
ZP2024-0070
ZP2024-0100
ZP2024-0116
ZP2024-0129
```
