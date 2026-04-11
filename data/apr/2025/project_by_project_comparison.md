# City APR vs Database: Project-by-Project Comparison

**Generated:** 2026-04-11
**APR Source:** 2026-03-27 Housing Element and General Plan Annual Progress Reports (PDF)
**Database:** berkeley_housing_analysis.db

---

## Summary

| Source | Project Count | Notes |
|--------|---------------|-------|
| City APR Table A | 16 applications | 755 proposed units, 471 approved |
| City APR Table A2 | ~30+ projects | Building activity (entitled, permitted, completed) |
| Database | 159 projects | All tracked projects |

---

## Completed Projects Comparison

| Address | City APR Units | DB Units | City APR VLI | DB VLI | City APR Status | DB Status | DB CO Date | Match? |
|---------|----------------|----------|--------------|--------|-----------------|-----------|------------|--------|
| 1367 UNIVERSITY Ave | 39 | 39 | 39 VLI | 39 | Completed | Completed | 2025-06-18 | ✓ |
| 1752 SHATTUCK Ave | 68 | 68 | 0 | 0 | Completed | Completed | 2025-05-27 | ✓ |
| 2001 ASHBY Ave | 87 | 87 | 86 VLI | 86 | Completed | Completed | 2025-06-01 | ✓ |
| 2127 DWIGHT Way | 58 | 58 | 8 VLI | 8 | Completed | Completed | 2025-03-03 | ✓ |
| 3030 TELEGRAPH Ave | 144 | 144 | 0 | 0 | Completed | Completed | 2026-01-27 | ✓ |
| 2555 COLLEGE Ave | 11 | 11 | 1 VLI | 1 | Completed | Completed | 2023-06-09 | ✓ |

**Completed Projects Summary:** All 6 major completed projects match between City APR and database.

---

## Table A - Housing Development Applications (2025)

Projects from City APR Table A (page 11) with database comparison:

| Address | APR Units | APR Status | DB Units | DB Status | Notes |
|---------|-----------|------------|----------|-----------|-------|
| 1740 UNIVERSITY Ave | 12 | Approved | 12 | Under Review | Status discrepancy |
| 2330 DURANT Ave | 68 | Under Review (SMAP) | — | Not in DB | New application |
| 2029 UNIVERSITY Ave | 160 | Approved | 160 | Entitled | Status may need update |
| 2029 UNIVERSITY Ave (Phase 2) | 240 | Under Review | 240 | — | Separate phase tracking |
| 2372 ELLSWORTH St | 49 | Under Review | 49 | Under Review | ✓ Match |
| 2598 TELEGRAPH Ave | 17 | Approved | 17 | Entitled | Status discrepancy |
| 2080 ALLSTON Way | 14 | Approved | 14 | Entitled | Status discrepancy |
| 2740 SAN PABLO Ave | 13 | Approved | 13 | Under Review | Status discrepancy |
| 1685 SOLANO Ave | 10 | Under Review | 10 | Under Review | ✓ Match |
| 1290 SIXTH St | 11 | Under Review | 11 | Under Review | ✓ Match |
| 2055 CENTER St | 49 | Approved | 49 | Entitled | Status discrepancy |
| 3000 SHATTUCK Ave | 50 | Under Review | 50 | Under Review | ✓ Match |
| 1701 UNIVERSITY Ave | 35 | Under Review | — | — | Check address |
| 2118 DWIGHT Way | 7 | Approved (SB 35) | — | — | New/not in DB |
| 2312 SAN PABLO Ave | 17 | Approved | — | — | Check DB |
| 1733 UNIVERSITY Ave | 3 | Under Review | — | — | Small project |

---

## Under Construction Projects

| Address | City APR Units | DB Units | DB VLI | DB BP Issued | Match? |
|---------|----------------|----------|--------|--------------|--------|
| 1701 SAN PABLO Ave | 110 | 110 | 110 | 2023-06-01 | ✓ |
| 1598 UNIVERSITY Ave | 207 | 207 | 21 | 2024-01-01 | ✓ |
| 2020 KITTREDGE St | 165 | 165 | 0 | 2024-01-01 | ✓ |
| 2028 KITTREDGE St | 126 | 126 | 13 | 2024-01-01 | ✓ |
| 2009 CHANNING Way | 75 | 75 | 75 | 2023-09-01 | ✓ |
| 1900 FOURTH St | 142 | 142 | 0 | 2023-01-01 | ✓ |
| 2067 UNIVERSITY Ave | 57 | 57 | 6 | 2022-11-01 | ✓ |

---

## Major Pipeline Projects

| Address | City APR Status | DB Status | DB Units | DB VLI | Notes |
|---------|-----------------|-----------|----------|--------|-------|
| Ashby BART | In Pipeline | Under Review | 618 | 309 | Major BART development |
| North Berkeley BART | In Pipeline | Under Review | 410 | 205 | Major BART development |
| 2190 SHATTUCK Ave | Entitled | Entitled | 261 | 26 | Downtown project |
| 2161 ALLSTON Way | Entitled | Entitled | 186 | 19 | Downtown project |

---

## Discrepancies Identified

### 1. Status Mismatches
Several projects show "Approved" in City APR but "Entitled" or "Under Review" in database:
- 1740 UNIVERSITY Ave: APR=Approved, DB=Under Review
- 2598 TELEGRAPH Ave: APR=Approved, DB=Entitled
- 2080 ALLSTON Way: APR=Approved, DB=Entitled
- 2740 SAN PABLO Ave: APR=Approved, DB=Under Review

**Action:** Update database statuses to reflect latest City approvals.

### 2. Projects in APR Not Found in Database
- 2330 DURANT Ave (68 units, SMAP)
- 2118 DWIGHT Way (7 units, SB 35)
- 1733 UNIVERSITY Ave (3 units)

**Action:** Add these new applications to database.

### 3. CO Date Discrepancies
- 3030 TELEGRAPH Ave: DB shows CO 2026-01-27 (after APR reporting period)

---

## RHNA Progress Comparison

| Category | City APR Progress | City APR Remaining |
|----------|-------------------|-------------------|
| Very Low Income | 244 | 2,002 |
| Low Income | 227 | 1,067 |
| Moderate Income | 97 | 1,368 |
| Above Moderate | 1,549 | 2,380 |
| **Total** | **2,117** | **6,817** |

---

## Recommendations

1. **Update status fields** in database for projects with new City approvals
2. **Add new applications** from Table A not currently in database
3. **Verify CO dates** for completed projects against City records
4. **Track SMAP/SB 35** streamlined projects separately
5. **Cross-reference** building permit numbers when available

---

## Data Quality Notes

- City APR Table A covers applications submitted in 2025 calendar year
- City APR Table A2 covers all building activity (entitled, permitted, completed)
- Database contains historical projects beyond current reporting year
- VLI counts in database align well with City affordability reporting
