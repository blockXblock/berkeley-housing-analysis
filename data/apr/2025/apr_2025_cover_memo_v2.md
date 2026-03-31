# City of Berkeley 2025 Annual Progress Report
## Cover Memo and Methodology - Version 2

**Reporting Period:** January 1, 2025 - December 31, 2025
**Due Date:** April 1, 2026
**Prepared by:** Berkeley Housing Pipeline Analysis Project
**Data as of:** March 30, 2026
**Version:** 2.0 (updated with latest scraped data)

---

## Executive Summary

This memo accompanies Berkeley's 2025 Annual Progress Report (APR) to the California Department of Housing and Community Development (HCD). The report covers housing development activity during calendar year 2025.

### Key Findings

| Metric | Previous (v1) | Updated (v2) | Change |
|--------|---------------|--------------|--------|
| **Total Pipeline** | 159 projects, 10,142 units | 162 projects, 10,155 units | +3 projects, +13 units |
| **Applications Complete in 2025** | 6 projects, 877 units | 6 projects, 877 units | No change |
| **Entitlements Granted in 2025** | 17 projects, 2,404 units | 17 projects, 2,404 units | No change |
| **Certificates of Occupancy in 2025** | 2 projects, 126 units | 2 projects, 126 units | No change |
| **VLI Units in Pipeline** | 905 units (63.2%) | 906 units (63.3%) | +1 unit |
| **RHNA Progress (Total)** | 10,142 units (113.5%) | 10,155 units (113.7%) | +13 units |

### Data Quality Improvements (v2)

| Metric | Previous | Updated | Improvement |
|--------|----------|---------|-------------|
| **APP_SUBMIT_DT populated** | ~40 projects | 61 projects | +21 projects |
| **Construction status tracking** | 7 projects | 17 projects | +10 projects |
| **Accela text files scraped** | 65 files | 75 files | +10 files |
| **Under Construction projects** | 7 projects | 8 projects | +1 project |

---

## Table A: Housing Development Applications (2025)

**Description:** Projects with application deemed complete during calendar year 2025.

**File:** `table_a_2025_v2.csv`

**Projects Included (6):**

| Address | Units | Complete Date | Status | Notes |
|---------|-------|---------------|--------|-------|
| 2276 Shattuck Ave | 336 | 2025-08-07 | In Review | SB-330, density bonus |
| 2425 Durant Ave | 250 | 2025-03-13 | Pending Final Action | SB-330, 13 VLI |
| 2029 University Ave | 240 | 2025-06-03 | Pending Final Action | 100% density bonus |
| 2614 Telegraph Ave | 31 | 2025-04-30 | Corrections Pending | 3 VLI, 2 LI |
| 1740 University Ave | 12 | 2025-09-15 | Approved | Conversion project |
| 2200 Fifth St | 8 | 2025-11-24 | Withdrawn | Townhouse project |

**Total:** 877 units across 6 projects (unchanged from v1)

---

## Table A2: Housing Development Activity (2025)

**Description:** All entitlement, building permit, or certificate of occupancy activity during 2025.

**File:** `table_a2_2025_v2.csv`

### Activity Summary

| Activity Type | Projects | Units | Change from v1 |
|--------------|----------|-------|----------------|
| Entitlements | 17 | 2,404 | No change |
| Building Permits | 0 | 0 | No change |
| Certificates of Occupancy | 2 | 126 | No change |
| Under Construction | 8 | 744 | +1 project |
| **Total Unique Projects** | **25** | **3,274** | -1 (deduplication) |

### Notable Entitlements (2025)

| Address | Units | VLI | Date | Type |
|---------|-------|-----|------|------|
| 1974 Shattuck Ave | 599 | 0 | 2025-06-03 | Density Bonus |
| 2276 Shattuck Ave | 336 | 9 | 2025-12-04 | SB-330 |
| 2425 Durant Ave | 250 | 13 | 2025-10-09 | SB-330 |
| 2029 University Ave | 240 | 18 | 2025-11-13 | Density Bonus |
| 2274 Shattuck Ave | 227 | 0 | 2025-04-22 | Density Bonus |
| 2100 Milvia St | 201 | 0 | 2025-07-01 | Mixed-use |
| 3000 Shattuck Ave | 166 | 17 | 2025-03-11 | Density Bonus |

### Certificates of Occupancy (2025)

| Address | Units | Affordable | CO Date | Developer |
|---------|-------|------------|---------|-----------|
| 2001 Ashby Ave | 87 | 86 (99%) | 2025-06-01 | Resources for Community Development |
| 1367 University Ave | 39 | 39 (100%) | 2025-07-01 | Panoramic Interests |

**Total CO'd:** 126 units (125 affordable, 99.2%)

### Under Construction Projects (Status-based)

| Address | Units | VLI | Construction Status |
|---------|-------|-----|---------------------|
| 1598 University Ave | 207 | 21 | topped_out |
| 3030 Telegraph Ave | 144 | 0 | finishing |
| 1701 San Pablo Ave | 110 | 110 | foundation |
| 2538 Durant Ave | 83 | 5 | foundation |
| 2127 Dwight Way | 58 | 8 | topped_out |
| 2902 Adeline St | 54 | 0 | framing |
| 2587 Telegraph Ave | 52 | 6 | topped_out |
| 2403 San Pablo Ave | 36 | 0 | foundation |

**Total Under Construction:** 744 units (150 VLI)

---

## Table B: RHNA Progress by Income Level

**Description:** Progress toward Regional Housing Needs Allocation (8th Cycle, 2023-2031).

**File:** `table_b_2025_v2.csv`

### RHNA Progress Summary

| Income Level | RHNA Target | Pipeline Units | % of Target | Change |
|--------------|-------------|----------------|-------------|--------|
| Very Low Income (VLI) | 1,432 | 906 | 63.3% | +0.1% |
| Low Income (LI) | 825 | 724 | 87.8% | No change |
| Moderate (MOD) | 1,416 | 452 | 31.9% | No change |
| Above Moderate | 5,261 | 8,073 | 153.5% | +0.3% |
| **Total** | **8,934** | **10,155** | **113.7%** | +0.2% |

### Key Observations

1. **Pipeline Growth:** 3 new projects added since v1, adding 13 net units to the pipeline.

2. **VLI Progress:** 906 documented VLI units (63.3% of target). Gap of 526 units remains to meet RHNA requirement.

3. **Above Moderate Surplus:** Berkeley continues to significantly exceed Above Moderate target (153.5%), driven by large market-rate projects on Shattuck and Telegraph corridors.

4. **Construction Activity:** 8 projects actively under construction with 744 total units, including 150 VLI units. Three projects are topped out and expected to deliver in 2026.

5. **100% Affordable Completions:** Both 2025 COs (2001 Ashby, 1367 University) were 100% affordable projects, demonstrating continued affordable housing delivery.

---

## Data Quality Assessment

### Improvements in v2

1. **Accela Scraping:** 10 additional project files scraped, bringing total to 75 validated text files.

2. **Construction Status Tracking:** New `construction_status` field populated for 17 projects with values: occupied (6), foundation (4), topped_out (3), framing (1), demolition (1), finishing (1), pending_bp (1).

3. **Date Coverage:**
   - `app_filed_date`: 61 of 162 projects (37.7%)
   - `app_complete_date`: 31 of 162 projects (19.1%)
   - `entitled_date`: 36 of 162 projects (22.2%)

### Known Gaps

| Gap | Impact | Status |
|-----|--------|--------|
| Building permit dates | 0 BP issued dates for 2025 | Need Building Division extract |
| ADU permits | ~95 units/year not captured | Separate tracking recommended |
| LI/MOD unit counts | Estimated from density bonus | Manual verification needed |
| In-lieu fee tracking | Cannot verify Trust Fund payments | Finance records required |

---

## Data Sources

### Primary Sources

1. **Accela Permit Records:** 75 validated text files with complete processing histories
2. **housing_projects_FINAL.csv:** Master dataset with 162 projects, 10,155 units
3. **permit_events table:** 755 processing events across 80 permits
4. **APR Cross-Reference:** Comparison against 2024 APR submission (37 matched projects)

### Methodology

- **Application Complete:** `app_complete_date` in 2025 (YYYY-01-01 to YYYY-12-31)
- **Entitlement:** `entitled_date` in 2025
- **Certificate of Occupancy:** `co_date` in 2025
- **Under Construction:** `status` contains "Construction" without documented CO

---

## Files Generated

| File | Description | Records |
|------|-------------|---------|
| `table_a_2025_v2.csv` | Applications complete in 2025 | 6 projects |
| `table_a2_2025_v2.csv` | All 2025 activity | 27 records, 25 unique projects |
| `table_b_2025_v2.csv` | RHNA progress | 5 income categories |

---

## Recommendations

1. **Building Permit Integration:** Extract BP issued dates from Building Division to complete Table A2.

2. **ADU Tracking:** Establish workflow to include ADU permits (estimated 95+ units/year).

3. **Automated APR Export:** Implement HCD-compatible export directly from Accela.

4. **Income Verification:** Manual review of LI/MOD unit counts in density bonus agreements.

5. **Construction Monitoring:** Continue updating `construction_status` field as projects progress.

---

## Certification

This data has been prepared using best available information from City records and public sources. Version 2 incorporates additional scraped data and improved construction status tracking.

**Analysis conducted by:** Berkeley Housing Pipeline Analysis Project
**Contact:** [City Planning Department]
**Date:** March 30, 2026

---

*This memo was generated as part of an independent housing data audit. For official APR submissions, verify all figures against City of Berkeley Planning Department records.*
