# Berkeley 2024 APR Table A Comparison (v3)

Generated: 2026-03-23 15:22

## Summary

| Dataset | Projects | Total Units |
|---------|----------|-------------|
| **City APR 2024** | 39 | 3,832 |
| **FINAL.csv (2024)** | 52 | 5,436 |
| **FINAL.csv (all years)** | 134 | - |

## Match Analysis

| Metric | Count |
|--------|-------|
| **City APR projects found in FINAL** | **37** of 39 (**94%**) |
| **Matched with year=2024** | 33 |
| **Matched but different year** | 4 |
| **City APR projects NOT in FINAL** | 2 |
| **FINAL 2024 projects NOT in city APR** | 20 |

### ✅ Coverage: 37/39 City Projects Found

We now have **37** of the city's **39** reported 2024 projects in our database.

## Unit Comparison

| Income Level | City APR | Our Data (2024) | Gap |
|--------------|----------|-----------------|-----|
| Very Low Income | 520 | 20 | 500 |
| Low Income | 136 | - | - |
| Moderate Income | 37 | - | - |
| Above Moderate | 3,139 | - | - |
| **Total** | 3,832 | 5,436 | -1,604 |

*Note: Our data has MORE units because we have 17 additional 2024 projects not in city APR.*

## Status Comparison

### City APR Status
| Status | Count |
|--------|-------|
| Pending | 27 |
| Approved | 12 |

### Our FINAL.csv Status (2024 only)
| Status | Count |
|--------|-------|
| Approved | 18 |
| Under Review | 12 |
| Pending Final Action | 8 |
| Corrections Pending Applicant | 6 |
| In Review | 3 |
| Incomplete Pending Applicant | 3 |
| Pending | 1 |
| Resubmittal Pending Review | 1 |


## Application Dates from permit_events

**14** of **37** matched projects have dates derivable from permit_events.

| Permit | City APP_SUBMIT_DT | Our Event Date | Match? |
|--------|-------------------|----------------|--------|
| ZP2022-0115 | 2024-12-06 | 2022-12-05 | ⚠️ |
| ZP2023-0064 | 2024-03-29 | 2024-03-29 | ✅ |
| ZP2023-0079 | 2024-01-04 | 2024-01-04 | ✅ |
| ZP2023-0107 | 2024-02-15 | 2023-11-16 | ⚠️ |
| ZP2023-0123 | 2024-02-26 | 2023-12-01 | ⚠️ |
| ZP2023-0126 | 2024-03-12 | 2024-03-12 | ✅ |
| ZP2023-0163 | 2024-05-17 | 2023-12-20 | ⚠️ |
| ZP2024-0008 | 2024-02-22 | 2024-02-20 | ⚠️ |
| ZP2024-0014 | 2024-02-29 | 2024-02-15 | ⚠️ |
| ZP2024-0029 | 2024-04-30 | 2024-04-30 | ✅ |
| ZP2024-0070 | 2024-10-08 | 2024-08-19 | ⚠️ |
| ZP2024-0116 | 2024-12-19 | 2024-12-05 | ⚠️ |
| ZP2024-0129 | 2024-10-18 | 2024-10-17 | ⚠️ |
| ZP2024-0162 | 2024-11-21 | 2025-02-13 | ⚠️ |


## Year Mismatches

These 4 city APR 2024 projects exist in our data but with different years:

| Permit | Address | City Says 2024 | Our Year | Our Units |
|--------|---------|----------------|----------|-----------|
| ZP2023-0099 | 2109 MILVIA St, BERKELEY, CA 94704 | 2024 | 2023 | 105 |
| ZP2023-0107 | 2462 BANCROFT Way, BERKELEY, CA 947 | 2024 | 2023 | 66 |
| ZP2023-0090 | 2733 SAN PABLO Ave, BERKELEY, CA 94 | 2024 | 2023 | 32 |
| ZP2024-0029 | 2680 BANCROFT Way, BERKELEY, CA 947 | 2024 | 2023 | 37 |


## Truly Unmatched City Projects

These 2 city APR projects are NOT in our FINAL.csv at all:

| Permit | Address | Units | Status |
|--------|---------|-------|--------|
| ZP2022-0038 | 2820 SAN PABLO Ave, BERKELEY, CA 94702 | 1 | Approved |
| ZP2024-0100 | 0 PARKER St, BERKELEY, CA 94703 | 1 | Approved |


## Extra FINAL Projects (not in City APR)

These 20 projects are in our FINAL.csv (year=2024) but NOT in city's APR:

| Permit | Address | Units | Status |
|--------|---------|-------|--------|
| ZP2023-00401974 | Shattuck | 599 | Approved |
| LMSAP2024-0005, ZP2024-00 | 2276 SHATTUCK Ave | 336 | In Review |
| ZP2024-0181, ZP2024-0182, | 2029 UNIVERSITY Ave | 240 | Pending Final Action |
| ZP2024-0075 | 1899 OXFORD St | 212 | Pending Final Action |
| ZP2024-0131 | 2115 KITTREDGE St | 148 | Incomplete Pending Applicant |
| ZP2024-0071 | 2955 SHATTUCK Ave | 74 | Corrections Pending Applicant |
| PLN2024-0023 | 2326 DURANT Ave | 70 | Pending |
| PLN2024-0054 | 2372 ELLSWORTH St | 63 | Under Review |
| PLN2024-0011 | 2138 KITTREDGE St | 63 | Under Review |
| ZP2024-0027 | 2614 TELEGRAPH Ave | 31 | Corrections Pending Applicant |
| PLN2024-0025 | 2428 MILVIA St | 8 | Under Review |
| PLN2024-0018 | 2317 CHANNING Way | 5 | Under Review |
| ZP2024-0147 | 2420 ASHBY Ave | 4 | Under Review |
| PLN2024-0001 | 2205 BLAKE St | 3 | Under Review |
| PLN2024-0013 | 2201 BLAKE St | 3 | Approved |
| ... | ... | ... | (5 more) |


## Data Quality Notes

1. **Year Classification**: Some projects have different years in our data vs city APR (application date vs when project activity occurred)
2. **Income Breakdown**: We extract VLI units from descriptions; city has full income tier breakdown
3. **Extra Projects**: Our database includes projects not yet in city's APR submission
4. **Permit Numbers**: Matching done by permit number first, then by normalized address

## Sources

- City APR: `data/reference/city_apr_2024_table_a.csv`
- Our data: `data/processed/housing_projects_FINAL.csv`
- Event dates: `databases/berkeley_housing_analysis.db` (permit_events table)
