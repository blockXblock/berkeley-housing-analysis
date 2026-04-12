# Cohort Staleness Analysis

Generated: 2026-03-23 11:32

Cutoff for staleness: 12 months (before 2025-03-23)

## Summary

| Metric | Count | Units |
|--------|-------|-------|
| Potentially Stalled (>12 mo inactive) | 19 | 1,464 |
| Active (<12 mo since last activity) | 5 | 952 |
| **Total Approved/Pending** | **24** | **2,416** |

## Potentially Stalled Projects

These projects have `Approved` or `Pending Final Action` status but show no permit activity in the past 12 months.

| Address | Units | Status | Permit | Last Activity | Days Since |
|---------|-------|--------|--------|---------------|------------|
| 1974 SHATTUCK Ave | 599 | Approved | ZP2023-0040 | None | NO DATA |
| 1899 OXFORD St | 212 | Pending Final Action | ZP2024-0075 | None | NO DATA |
| 2109 VIRGINIA St | 131 | Approved | ZP2024-0066 | None | NO DATA |
| 2530 BANCROFT Way | 110 | Approved | ZP2023-0126 | 2024-12-27 | 451 |
| 2655 SHATTUCK Ave | 97 | Pending Final Action | ZP2024-0057 | None | NO DATA |
| 2037 DURANT Ave | 74 | Approved | ZP2023-0064 | 2024-06-19 | 642 |
| 2462 BANCROFT Way | 66 | Approved | ZP2023-0107 | None | NO DATA |
| 2138 KITTREDGE St | 66 | Approved | ZP2024-0114 | None | NO DATA |
| 2298 DURANT Ave | 65 | Pending Final Action | ZP2024-0126 | None | NO DATA |
| 2317 CHANNING Way | 22 | Approved | ZP2024-0033 | None | NO DATA |
| 2147 SAN PABLO Ave | 15 | Pending Final Action | ZP2024-0096 | None | NO DATA |
| 2201 BLAKE St | 3 | Approved | PLN2024-0013 | None | NO DATA |
| 2204 DWIGHT Way | 2 | Pending Final Action | ZP2024-0059 | None | NO DATA |
| 3001 BENVENUE Ave | 1 | Pending Final Action | ZP2025-0068 | None | NO DATA |
| 1420 FIFTH St | 1 | Pending Final Action | ZP2025-0021 | None | NO DATA |
| 3035 COLBY St | 0 | Approved | ZP2024-0112 | None | NO DATA |
| 2145 GRANT St | 0 | Pending Final Action | ZP2024-0138 | None | NO DATA |
| 1187 SHATTUCK Ave | 0 | Pending Final Action | ZP2025-0088 | None | NO DATA |
| 830 BANCROFT Way | 0 | Pending Final Action | ZP2025-0096 | None | NO DATA |

## Active Projects

| Address | Units | Status | Permit | Last Activity | Days Since |
|---------|-------|--------|--------|---------------|------------|
| 2425 DURANT Ave | 250 | Pending Final Action | ZP2024-0162 | 2025-12-26 | 87 |
| 2029 UNIVERSITY Ave | 240 | Pending Final Action | ZP2024-0181 | 2025-11-17 | 126 |
| 2274 SHATTUCK Ave | 227 | Approved | ZP2023-0079 | 2025-04-22 | 335 |
| 2100 MILVIA St | 201 | Approved | ZP2023-0163 | 2025-07-01 | 265 |
| 2442 HASTE St | 34 | Approved | ZP2024-0070 | 2025-09-08 | 196 |

## Missing Project: ZP2022-0135 (2128 Oxford)

**This 456-unit project is COMPLETELY MISSING from our databases.**

| Field | Value |
|-------|-------|
| Permit | ZP2022-0135 |
| Address | 2128 Oxford St |
| Units | 456 |
| Height | 27 stories (285 ft) - Berkeley's tallest approved building |
| Developer | Core Spaces (Chicago) |
| Architect | DLR Group |
| Approved | September 2024 (ZAB) |
| Status | Approved - Demolition permits filed |
| Affordable | 40 units (6 ELI + 34 VLI) |

**Sources:**
- [SF YIMBY: Berkeley Gives Approval For Tallest Building Yet](https://sfyimby.com/2024/09/berkeley-gives-approval-for-tallest-building-yet-at-2128-oxford-street.html)
- [Urbanize: 26-story, 456-unit project proposed](https://sf.urbanize.city/post/26-story-456-unit-project-proposed-2128-oxford-berkeley)
- [CEQA: 2128 Oxford Street Mixed-Use Project](https://ceqanet.opr.ca.gov/2023080040/2)

## Data Quality Issues

1. **Many projects have NO activity data** - permit_events table only has 20 permits
2. **Fee data is sparse** - only 4 permits have fee payment records
3. **Major project missing** - ZP2022-0135 (456 units) not in any table
4. **Need to scrape** - Run `discover --year 2022 --find-gaps` to identify more missing 2022 permits
