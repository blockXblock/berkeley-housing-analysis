# City APR vs Database: Project-by-Project Comparison v2

**Generated:** 2026-04-11 11:55
**City Source:** 2026-03-27 Housing Element APR - Table A2
**Database:** berkeley_housing_analysis.db

---

## Summary

| Source | Count | Notes |
|--------|-------|-------|
| City APR Table A2 | 235 projects | 178 ADUs, 26 major (5+) |
| Database | 164 projects | Primarily 5+ unit projects |
| Matched | 22 projects | Found in both sources |
| City-only | 213 projects | Need to add/scrape |
| DB-only (5+ units) | 73 projects | Not in City APR |
| Discrepancies | 16 projects | Units/VLI mismatch |

---

## Matched Projects

### Major Projects (5+ units)

| City Address | Permit | City Units | DB Units | City VLI | DB VLI | DB Status | Match? |
|--------------|--------|------------|----------|----------|--------|-----------|--------|
| 1740 SAN PABLO Ave | B2022-05881 | 54 | 54 | 6 | 0 | Under Review | ✓ |
| 2403 SAN PABLO AVE | B2024-00143 | 36 | 36 | 0 | 0 | Under Construction | ✓ |
| 1701 SAN PABLO AVE | B2024-02966 | 110 | 110 | 20 | 110 | Under Construction | ✓ |
| 2300 Ellsworth Street | B2024-05944 | 69 | 69 | 2 | 0 | Under Review | ✓ |
| 2902 ADELINE ST | B2021-04232 | 54 | 54 | 4 | 0 | Under Construction | ✓ |
| 2480 BANCROFT Way | B2022-05880 | 28 | 28 | 2 | 0 | Stalled | ✓ |
| 2555 COLLEGE Ave | B2023-02975 | 11 | 11 | 1 | 1 | Completed | ✓ |
| 2550 Shattuck Ave | ZP2023-0138 | 75 | 72 | 8 | 15 | Under Review | **MISMATCH** |
| 2680 BANCROFT Way | ZP2024-0029 | 79 | 37 | 9 | 0 | Entitled | **MISMATCH** |
| 2317 CHANNING Way | ZP2024-0033 | 22 | 5 | 0 | 0 | Under Review | **MISMATCH** |
| 1974 SHATTUCK Ave, BERKELEY | ZP2023-0040 | 599 | 599 | 58 | 0 | Entitled | ✓ |
| 2274 SHATTUCK Ave | ZP2023-0079 | 227 | 227 | 23 | 0 | Entitled | ✓ |
| 2442 HASTE St | ZP2024-0070 | 38 | 38 | 1 | 2 | Entitled | ✓ |
| 2372 ELLSWORTH St | ZP2024-0169 | 49 | 63 | 0 | 0 | Under Review | **MISMATCH** |
| 2138 KITTREDGE St | ZP2024-0114 | 66 | 63 | 3 | 5 | Entitled | **MISMATCH** |
| 2100 MILVIA St | ZP2023-0163 | 0 | 201 | 9 | 0 | Entitled | **MISMATCH** |
| 2942 COLLEGE Ave | ZP2022-0136 | 6 | 4 | 0 | 0 | Under Review | **MISMATCH** |

### ADU/Small Projects (5 matches)

Most ADUs match correctly (1-2 units each). Not listed individually.

---

## Discrepancies

Projects where City APR and database differ:

| Address | Permit | City Units | DB Units | City VLI | DB VLI | Issue |
|---------|--------|------------|----------|----------|--------|-------|
| 1740 SAN PABLO Ave | B2022-05881 | 54 | 54 | 6 | 0 | VLI diff: 6 |
| 1701 SAN PABLO AVE | B2024-02966 | 110 | 110 | 20 | 110 | VLI diff: 90 |
| 1614 Sixth Street | B2024-04504 | 1 | 3 | 0 | 0 | Units diff: 2 |
| 2300 Ellsworth Street | B2024-05944 | 69 | 69 | 2 | 0 | VLI diff: 2 |
| 2902 ADELINE ST | B2021-04232 | 54 | 54 | 4 | 0 | VLI diff: 4 |
| 2480 BANCROFT Way | B2022-05880 | 28 | 28 | 2 | 0 | VLI diff: 2 |
| 2550 Shattuck Ave | ZP2023-0138 | 75 | 72 | 8 | 15 | Units diff: 3, VLI diff: 7 |
| 2680 BANCROFT Way | ZP2024-0029 | 79 | 37 | 9 | 0 | Units diff: 42, VLI diff: 9 |
| 2317 CHANNING Way | ZP2024-0033 | 22 | 5 | 0 | 0 | Units diff: 17 |
| 1974 SHATTUCK Ave, BERKELEY | ZP2023-0040 | 599 | 599 | 58 | 0 | VLI diff: 58 |
| 2274 SHATTUCK Ave | ZP2023-0079 | 227 | 227 | 23 | 0 | VLI diff: 23 |
| 2372 ELLSWORTH St | ZP2024-0169 | 49 | 63 | 0 | 0 | Units diff: 14 |
| 2138 KITTREDGE St | ZP2024-0114 | 66 | 63 | 3 | 5 | Units diff: 3, VLI diff: 2 |
| 2100 MILVIA St | ZP2023-0163 | 0 | 201 | 9 | 0 | Units diff: 201, VLI diff: 9 |
| 2942 COLLEGE Ave | ZP2022-0136 | 6 | 4 | 0 | 0 | Units diff: 2 |

---

## Projects in City APR but NOT in Database

These need to be added to our database or scraped from Accela:

### Major Projects (5+ units) - 9 projects

| Address | Permit | Units (Ent/BP/CO) | VLI | BP Date | CO Date |
|---------|--------|-------------------|-----|---------|---------|
| 1463 Sixth Street | B2024-02508 | 3/3/0 | 0 | 9/18/2025 | nan |
| 2650 TELEGRAPH Ave | B2021-02225 | 0/0/45 | 4 | nan | 6/16/2025 |
| 2000 DWIGHT Way | B2021-02404 | 0/0/113 | 0 | nan | 6/17/2025 |
| St 2001 ASHBY Ave | B2021-02905 | 0/0/87 | 80 | nan | 2/24/2025 |
| 2440 SHATTUCK Ave | B2022-05117 | 0/0/40 | 3 | nan | 3/5/2025 |
| 1773 OXFORD St | B2023-02354 | 0/0/24 | 3 | nan | 4/21/2025 |
| 2435 SAN PABLO Ave | ZP2024-0120 | 1/0/0 | 0 | nan | nan |
| 1698 UNIVERSITY | B2014-05752 | 0/0/36 | 0 | nan | 5/22/2025 |
| 1812 UNIVERSITY Ave | B2019-05321 | 0/0/2 | 0 | nan | 9/2/2025 |

### Multi-family (2-4 units) - 7 projects

| Address | Permit | Units |
|---------|--------|-------|
| 1729 Eighth | B2024-03463 | 2 |
| 2708 Prince | B2024-06003 | 2 |
| 1173 HEARST AVE | B2024-01117 | 2 |
| 1828 EUCLID | B2021-03440 | 0 |
| Ave 2737 DURANT Ave | B2021-04892 | 0 |
| 924 CARLETON St | ZP2023-0094 | 4 |
| 2325 SIXTH St | B2020-01409 | 0 |

### Single-Family Detached - 20 projects

*SFD projects typically not tracked in housing database*

### ADUs - 176 projects

*ADUs typically not tracked individually in housing database*

---

## Projects in Database but NOT in City APR

These projects are in our database but not in the City's 2025 APR Table A2.
This is expected for projects entitled/permitted in prior years.

| Address | Units | VLI | Status | BP Date | CO Date |
|---------|-------|-----|--------|---------|---------|
| 2200 BANCROFT Way | 550 | 0 | Under Construction |  |  |
| 1598 UNIVERSITY Ave | 207 | 21 | Under Construction | 2024-01-01 |  |
| 2538 DURANT Ave | 83 | 5 | Under Construction | 2024-10-01 |  |
| 2587 TELEGRAPH Ave | 52 | 6 | Under Construction | 2024-01-01 |  |
| 2016 ASHBY Ave | 50 | 50 | Under Construction | 2024-06-01 |  |
| 3030 TELEGRAPH Ave | 144 | 0 | Completed | 2023-10-01 | 2026-01-27 |
| 2001 ASHBY Ave | 87 | 86 | Completed | 2022-02-04 | 2025-06-01 |
| 1752 SHATTUCK Ave | 68 | 0 | Completed | 2024-06-13 | 2025-05-27 |
| 2127 DWIGHT Way | 58 | 8 | Completed | 2024-01-01 | 2025-03-03 |
| 1367 UNIVERSITY Ave | 39 | 39 | Completed | 2023-03-13 | 2025-06-18 |
| 1951 Shattuck Ave | 0 | 0 | Completed |  | 2024-01-01 |
| 2000 University Ave | 0 | 0 | Completed |  | 2024-01-01 |
| 2099 MLK Jr Way | 0 | 0 | Completed |  | 2024-01-01 |
| 2150 Kittredge St | 0 | 0 | Completed |  | 2024-01-01 |
| 1750 SACRAMENTO St | 739 | 0 | Entitled |  |  |
| 2276 SHATTUCK Ave | 336 | 0 | Entitled |  |  |
| 2425 DURANT Ave | 250 | 0 | Entitled |  | 2000-12-31 |
| 2029 UNIVERSITY Ave | 240 | 0 | Entitled |  |  |
| 1899 OXFORD St | 212 | 0 | Entitled |  |  |
| 2109 VIRGINIA St | 131 | 0 | Entitled |  |  |
| 2198 SAN PABLO Ave | 100 | 0 | Entitled |  |  |
| 2655 SHATTUCK Ave | 97 | 0 | Entitled |  |  |
| 2147 SAN PABLO Ave | 15 | 0 | Entitled |  |  |
| 1740 UNIVERSITY Ave | 12 | 0 | Entitled |  |  |
| Ashby BART | 618 | 309 | Under Review |  |  |
| 2190 SHATTUCK Ave | 452 | 0 | Under Review |  |  |
| 2700 SHATTUCK Ave | 359 | 0 | Under Review |  |  |
| 1914 FIFTH St | 257 | 26 | Under Review |  |  |
| 2601 SAN PABLO Ave | 223 | 0 | Under Review |  | 2015-12-31 |
| 2920 SHATTUCK Ave | 221 | 0 | Under Review |  |  |
| 1581 UNIVERSITY Ave | 158 | 0 | Under Review |  |  |
| 2115 KITTREDGE St | 148 | 12 | Under Review |  |  |
| 2420 SHATTUCK Ave | 132 | 0 | Under Review |  | 2015-12-31 |
| 2847 SHATTUCK Ave | 132 | 0 | Under Review |  |  |
| 2720 SAN PABLO Ave | 113 | 9 | Under Review |  |  |
| 2109 MILVIA St | 105 | 0 | Under Review |  |  |
| 2450 SHATTUCK Ave | 94 | 0 | Under Review |  |  |
| 1700 SACRAMENTO St | 85 | 0 | Under Review |  |  |
| 2036 BANCROFT Way | 85 | 4 | Under Review |  |  |
| 2660 BANCROFT Way | 78 | 0 | Under Review |  |  |
| ... | ... | ... | ... | ... | ... |
| *33 more projects* | | | | | |

---

## Analysis

### Why Low Match Rate?

1. **ADU Focus**: City APR Table A2 includes 178 ADUs (76% of rows)
2. **Our DB Focus**: Our database tracks primarily 5+ unit projects
3. **Timeframe**: Table A2 covers 2025 building activity only
4. **Address Formatting**: Some addresses may not match due to formatting differences

### Key Observations

1. **Major projects match well**: Most 5+ unit projects are in both sources
2. **ADUs not tracked**: 178 ADU permits in city data not in our database
3. **Historical projects**: Many DB projects are from prior years (pre-2025)

### Recommended Actions

1. **Add major projects**: Any 5+ unit city projects not in DB should be added
2. **Update statuses**: Use city APR dates to update BP/CO dates
3. **Verify discrepancies**: Check unit counts where they differ significantly
4. **Consider ADU tracking**: Decide if ADUs should be tracked separately

### Potential City Data Issues

**Duplicate addresses in City APR:**

- 2124 PARKER ST: 2 entries
- 3019 BATEMAN St: 2 entries
- 1330 HASKELL ST: 2 entries
- 1340 HASKELL ST: 2 entries
- 2501 MABEL St: 2 entries
- 1916 Alcatraz Avenue: 2 entries

**Known issues to verify:**

- 2029 UNIVERSITY Ave: May be double-counted as Phase 1 + Phase 2
- 1974 SHATTUCK Ave: 599 units seems very large for this location

---

## Data Sources

- City APR PDF: `pdf/2026-03-27  Housing Element and General Plan Annual Progress Reports.pdf`
- Extracted Table A2: `data/raw/city_apr_2025_table_a2.csv`
- Database: `databases/berkeley_housing_analysis.db`
