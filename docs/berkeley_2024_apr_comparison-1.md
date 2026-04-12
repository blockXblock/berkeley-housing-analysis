# Berkeley 2024 APR: City's Report vs Our Draft — Key Comparisons

## Table A: Applications Submitted (2024)

| Metric | City's APR | Our Draft | Delta | Notes |
|--------|-----------|-----------|-------|-------|
| Total Projects | 39 | 39 | 0 | Match! |
| Total Proposed Units | 3,832 | 3,508 | +324 | City reports higher — need to check specific projects |
| Total Approved Units | 1,235 | — | — | City tracks entitlements in same year |
| VLI (Deed Restricted) | 497 | 88 | +409 | HUGE gap — city includes entitlements from prior-year apps |
| LI (Deed Restricted) | 136 | 35 | +101 | Same issue |
| MOD (Deed Restricted) | 37 | 41 | -4 | Close |
| Above Moderate | 3,139 | 3,344 | -205 | Inverse of above |

### Key Discrepancy: Income Unit Counts
The city's Table A summary shows 497 VLI-DR + 23 VLI-NDR = 520 VLI total across applications.
Our draft extracted only 88 VLI from descriptions. This means:
- Description parsing missed many affordability details
- Some projects have affordability set by formula (e.g., density bonus %)
- ADU affordability uses ABAG methodology (30/30/30/10 split)

## Table A2: Building Activity (Entitled + Permitted + Completed)

### City's Reported Totals
| Activity | VLI-DR | VLI-NDR | LI-DR | LI-NDR | MOD-DR | MOD-NDR | Above Mod | Total |
|----------|--------|---------|-------|--------|--------|---------|-----------|-------|
| Entitled | 351 | 31 | 135 | 31 | 1 | 30 | 1,458 | 2,037 |
| Bldg Permits | 47 | 31 | 4 | 31 | 0 | 30 | 588 | 731 |
| COs Issued | 30 | 28 | 25 | 27 | 0 | 27 | 571 | 708 |

### Building Permits by Structure Type
| Type | Entitled | Permitted | Completed |
|------|----------|-----------|-----------|
| SFA | 0 | 0 | 0 |
| SFD | 7 | 16 | 6 |
| 2-4 | 8 | 19 | 5 |
| 5+ | 1,920 | 594 | 606 |
| ADU | 102 | 102 | 91 |
| MH | 0 | 0 | 0 |
| **Total** | **2,037** | **731** | **708** |

### Critical: ADU Affordability Methodology
City uses ABAG methodology for ADU affordability:
- 30% Very Low Income
- 30% Low Income  
- 30% Moderate Income
- 10% Above Moderate Income
This accounts for a LARGE portion of the affordable unit counts in building permits.

102 ADUs permitted × 30% = ~31 VLI, ~31 LI, ~30 MOD from ADUs alone.

## Table B: RHNA Progress (Building Permits = RHNA Credit)

| Income Level | RHNA | Projection Period | 2023 | 2024 | Total | Remaining |
|-------------|------|-------------------|------|------|-------|-----------|
| Very Low | 2,446 | 25 | 57 | 78 | 160 | 2,286 |
| Low | 1,408 | 0 | 32 | 35 | 67 | 1,341 |
| Moderate | 1,416 | 25 | 28 | 30 | 83 | 1,333 |
| Above Moderate | 3,664 | 442 | 314 | 588 | 1,344 | 2,320 |
| **Total** | **8,934** | **492** | **431** | **731** | **1,654** | **7,280** |

Berkeley has permitted 18.5% of RHNA after 2 of 8 years (25% of cycle elapsed).

## Other Key Data Points from City's Report
- 20 density bonus applications submitted
- 4 projects permitted with density bonus (360 units)
- 83% of approved 5+ unit projects used State Density Bonus
- 2 SB 9 duplex projects, 0 AB 2011 permitted, 0 SB 423
- 119 infill projects permitted (501 units)
- City acknowledges data discrepancies with HCD prepopulated data

## What Our Dataset Is Missing

1. **102 ADU projects** — entirely absent from housing_projects_FINAL.csv (which only tracks zoning permits). ADUs go straight to building permits.
2. **Building permit dates** — city has specific BP issue dates for all 731 units
3. **CO dates** — city has specific CO dates for 708 completed units  
4. **Prior-year entitlements** — city's Table A2 includes projects from 2022-2023 that got BPs in 2024
5. **Income breakdowns using ABAG ADU methodology** — we need to apply same formula
6. **SFD projects** — city reports ~16 SFD building permits we don't track
