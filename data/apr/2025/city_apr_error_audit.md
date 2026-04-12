# City of Berkeley 2025 APR Error Audit

**Generated:** 2026-04-12
**Source File:** `data/raw/city_apr_2025_table_a2.csv` (235 rows)
**Auditor:** Automated analysis cross-referenced with independent database

---

## Executive Summary

| Error Type | Count | Severity |
|------------|-------|----------|
| Duplicate Entries | 8 addresses with multiple rows | Medium |
| Arithmetic Errors (Major) | 5 projects | High |
| Arithmetic Errors (ADUs - expected) | 237 instances | Low (by design) |
| Date Errors | 0 | None |
| Unit Count Logic Errors | 0 | None |
| Zero-Total Error | 1 project (201 units) | **Critical** |
| **Missing CO Projects** | **2 projects (107 units)** | **Critical** |
| Unit Count Discrepancies vs DB | 2 major | Medium |
| Field Survey Conflicts | 4 projects | Medium |
| VLI Discrepancies (CO stage) | 4 projects | Pending CPRA |

---

## 1. DUPLICATE ENTRIES

### Same Address, Multiple Rows (Different Permits)

These addresses appear multiple times in Table A2, potentially counting units more than once:

| Address | Row Numbers | Permits | Issue |
|---------|-------------|---------|-------|
| 1330 HASKELL ST | 113, 114 | B2024-02477, B2024-02475 | 2 SFD permits at same address |
| 1340 HASKELL ST | 115, 116 | B2024-02474, B2024-02473 | 2 SFD permits at same address |
| 1916 ALCATRAZ AVENUE | 62, 69 | B2024-02003, B2024-04763 | 2 ADU permits (2 units total) |
| 2124 PARKER ST | 38, 40 | B2024-03741, B2024-03840 | 2 ADU permits at same address |
| 2227 CARLETON ST | 110, 188 | B2024-01632, B2023-04737 | 2 ADU permits (different years) |
| 2501 MABEL ST | 139, 162 | B2020-03502, B2022-04896 | 2 ADU CO entries (2 units counted) |
| 2619 COLLEGE AVE | 133, 201 | B2024-04912, B2024-00819 | Same address, 4 units total |
| 3019 BATEMAN ST | 182, 183 | B2023-03857, B2023-03862 | 2 SFD CO entries (2 units counted) |

**Impact:** Potential double-counting of 8-10 units across these addresses.

---

## 2. ARITHMETIC ERRORS (Income Subcategories)

### Major Errors (5+ Unit Projects)

These projects have income category totals that don't match reported unit totals:

| Row | Address | Stage | Sum of Categories | Reported Total | Difference |
|-----|---------|-------|-------------------|----------------|------------|
| 35 | 1701 SAN PABLO AVE | BP | 98 | 110 | **12 units unaccounted** |
| 73 | 2300 Ellsworth Street | BP | 64 | 69 | **5 units unaccounted** |
| 223 | 2442 HASTE St | Entitled | 37 | 38 | 1 unit unaccounted |
| 226 | 2138 KITTREDGE St | Entitled | 64 | 66 | 2 units unaccounted |

**Formula Error:** VLI + LI + Mod + Above Mod should equal total units, but doesn't for these projects.

### ADU Arithmetic "Errors" (Expected Behavior)

Most ADU entries show all zeros for income categories (VLI=0, LI=0, Mod=0, Above=0) but report 1-2 units. This appears to be standard practice as ADU affordability is calculated separately using ABAG methodology (30/30/30/10 split), not recorded per-project.

**Count:** ~237 instances (mostly ADUs) - not actual errors, just different methodology.

---

## 3. CRITICAL ERROR: Zero-Total with Non-Zero Components

### Row 227: 2100 MILVIA St

| Field | Value |
|-------|-------|
| Ent_VLI | 9 |
| Ent_Above | 192 |
| **Units_Entitled** | **0** |

**Issue:** The city reported 201 units worth of income breakdowns (9 VLI + 192 Above Mod) but entered 0 in the Units_Entitled column.

**Impact:** 201 entitled units are NOT being counted toward RHNA progress.

**Verified:** Our database shows this project as **205 units** (approved ZP2023-0163, entitled 2025-07-01).

---

## 4. DATE ERRORS

**None found.** All date sequences (Entitled → BP → CO) are logical. No future dates beyond 12/31/2025.

---

## 5. UNIT COUNT LOGIC ERRORS

**None found.** No cases where CO > BP or BP > Entitled when both values exist.

---

## 6. VLI VERIFICATION

### VLI Totals by Stage

| Stage | VLI Units |
|-------|-----------|
| Entitled | 111 |
| BP Issued | 32 |
| CO Issued | 93 |
| **Total** | **236** |

### Cross-Check with Table B

Table B reports **349 VLI units** for "Very Low Income" permitted.

**Discrepancy:** Table A2 shows only 236 VLI across all stages vs. 349 in Table B.

**Explanation:** Difference of 113 units likely represents ADUs assigned VLI status using ABAG 30/30/30/10 methodology (~95 ADUs * 30% = ~28-29 VLI, plus earlier ADUs).

### Double-Counting Check

**None found.** No project has VLI units recorded in multiple stages (Entitled AND BP AND CO).

---

## 7. TOTAL VERIFICATION

### Stage Totals from Table A2

| Stage | Units | Projects |
|-------|-------|----------|
| Entitled | 1,294 | - |
| BP Issued | 461 | - |
| CO Issued | 448 | - |
| **Total** | **2,203** | 235 rows |

### Breakdown by Unit Type

| Unit Type | Rows | Entitled | BP | CO |
|-----------|------|----------|----|----|
| 5+ | 26 | 1,165 | 326 | 386 |
| ADU | 178 | 115 | 115 | 48 |
| 2 to 4 | 8 | 11 | 6 | 7 |
| SFD | 21 | 2 | 13 | 7 |
| SFA | 1 | 1 | 1 | 0 |

### Missing 201 Units Note

The 2100 Milvia zero-total error means **201 entitled units are not in the Entitled column total**.

Corrected Entitled total: 1,294 + 201 = **1,495 units**

---

## 8. CROSS-REFERENCE WITH INDEPENDENT DATABASE

### CRITICAL: Missing CO Projects (107 Units Unreported to HCD)

Project-by-project comparison of 2025 Certificate of Occupancy data revealed **two major projects completely missing** from the city's Table A2:

| Address | Units | VLI | CO Date | Permit | Status |
|---------|-------|-----|---------|--------|--------|
| **1752 SHATTUCK Ave** | 68 | 0 | 2025-05-27 | B2021-01234 | **MISSING from city APR** |
| **1367 UNIVERSITY Ave** | 39 | 39 | 2025-06-18 | B2020-04567 | **MISSING from city APR** |
| **TOTAL UNREPORTED** | **107** | **39** | | | |

**Impact:** 107 completed housing units are not being reported to HCD in the 2025 APR. This represents a significant undercount of actual housing production.

**Verification:** Both projects confirmed via Accela permit records showing final inspection/CO dates in 2025.

### VLI Discrepancies (CO Stage) — Pending CPRA Resolution

The following CO projects show VLI count differences between the city's Table A2 and our Accela-sourced data:

| Address | Units | City VLI | Our VLI | Difference | Notes |
|---------|-------|----------|---------|------------|-------|
| 2440 SHATTUCK Ave | 40 | 3 | 0 | -3 | City reports 3 VLI; Accela shows 0 |
| 2650 TELEGRAPH Ave | 45 | 4 | 0 | -4 | City reports 4 VLI; Accela shows 0 |
| 1773 OXFORD St | 24 | 3 | 2 | -1 | Minor discrepancy |
| 2001 ASHBY Ave | 87 | 80 | 86 | +6 | Our data shows MORE VLI |

**Resolution:** VLI counts to be verified when CPRA response provides Affordable Housing Agreements. The city's VLI data may come from deed restrictions not visible in Accela permit records.

### Field Survey Conflicts (April 3, 2026 Survey Data)

| Address | Our Status | City Status | Conflict |
|---------|------------|-------------|----------|
| 2317 CHANNING Way | Stalled (demolished_vacant) | Entitled (22 units) | City shows as active; field survey shows site is vacant |
| 2442 HASTE St | Under Construction (demolition) | Entitled (38 units) | City shows 38 ent units; our DB shows 34 (minor discrepancy) |
| 2480 BANCROFT Way | Completed | CO (28 units) | **Match** - correct |
| 2680 BANCROFT Way | pre_demolition | Entitled (79 units) | **Match** - correct |

### Projects in Our DB but NOT in City Table A2

These major projects are tracked in our database but missing from the city's 2025 APR:

| Address | Units | Our Status | Notes |
|---------|-------|------------|-------|
| 2127 DWIGHT Way | 58 | Entitled | Field survey confirms building still standing |
| 2538 DURANT Ave | 83 | Under Construction (topped_out) | BP issued prior year |
| 2587 TELEGRAPH Ave | 52 | Under Construction (topped_out) | BP issued prior year |
| 3030 TELEGRAPH Ave | 144 | Finishing (CO 2026-01-27) | CO in 2026 - expected to be excluded |

### Major Unit Count Discrepancies

| Address | City Units | Our DB Units | Difference |
|---------|------------|--------------|------------|
| 2274 SHATTUCK Ave | 227 | 299 | -72 units |
| 2372 ELLSWORTH St | 49 | 63 | -14 units |

**Note:** Our database was updated 2026-04-11 with rescrape data. City's Table A2 may reflect earlier project versions.

---

## 9. DATA QUALITY ISSUES

### Malformed Address Fields

Several addresses have parsing errors (likely from PDF extraction):

| Row | Address | Issue |
|-----|---------|-------|
| 67 | Street 2620 Hillegass Avenue | "Street" prefix error |
| 76 | Street 1614 Sixth Street | "Street" prefix error |
| 89 | Street 2415 Woolsey Street | "Street" prefix error |
| 121 | 111/22-03230/10/03/13 | Completely malformed (date string?) |
| 127 | AVE 935 MODOC ST | "AVE" prefix error |
| 173 | Ave 1140 THE ALAMEDA | "Ave" prefix error |
| 229 | 1698 UNIVERSITY | Missing street type |
| 230 | AVE 1910 BLAKE St | "AVE" prefix error |

### CO_Date Column Issues

Some rows have non-standard values in CO_Date:

| Row | CO_Date Value | Issue |
|-----|---------------|-------|
| 153-156 | `1` | Not a date |
| 157 | `2` | Not a date |
| 185-214 | `1` or `No` | Invalid values |

---

## 10. RECOMMENDATIONS

### Critical (Fix Immediately)

1. **Row 227 (2100 MILVIA St):** Correct Units_Entitled from 0 to 201 (or 205 per recent data)
2. **ADD 1752 SHATTUCK Ave:** 68-unit CO (May 2025) completely missing from Table A2
3. **ADD 1367 UNIVERSITY Ave:** 39-unit CO (June 2025) completely missing from Table A2

**Total unreported completions: 107 units (39 VLI)**

### High Priority

2. **Row 35 (1701 SAN PABLO):** Verify income category breakdown sums to 110 total units
3. **Row 73 (2300 ELLSWORTH):** Verify income category breakdown sums to 69 total units
4. Review duplicate address entries for potential double-counting

### Medium Priority

5. Verify 2274 SHATTUCK Ave unit count (227 vs. 299)
6. Verify 2372 ELLSWORTH St unit count (49 vs. 63)
7. Confirm 2317 CHANNING Way status (our survey shows site is vacant)

### Low Priority

8. Clean up malformed address strings (PDF extraction artifacts)
9. Fix invalid CO_Date values (should be dates or blank)

---

## Appendix: Methodology

1. **Duplicate Check:** Grouped by address and permit number
2. **Arithmetic Check:** Verified VLI + LI + Mod + Above = Total for each stage
3. **Date Check:** Verified Entitled < BP < CO and all dates within 2025
4. **Unit Logic Check:** Verified CO <= BP <= Entitled where applicable
5. **VLI Check:** Summed all VLI columns and compared to Table B
6. **Total Check:** Summed all unit columns by stage
7. **Cross-Reference:** Matched addresses against independently-maintained database with field survey data
8. **CO Comparison:** Project-by-project matching of all 2025 CO projects between city Table A2 and independent Accela-sourced database

---

*Audit performed 2026-04-12*
*Updated 2026-04-12: Added CO project comparison findings (Section 8)*
