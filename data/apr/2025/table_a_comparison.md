# Table A Comparison: Our Data vs City APR

**Generated:** 2026-04-15
**Reporting Period:** 2025 Calendar Year
**Sources:**
- Our Table A: `table_a_2025_v3.csv` (Accela-verified)
- City Table A: 2026-03-27 Housing Element APR (PDF page 11)

---

## Summary

| Source | Rows | Total Units | Notes |
|--------|------|-------------|-------|
| **Our Table A** | 6 | 745 | Accela-verified applications |
| **City Table A** | 17 | 856 | Includes errors (see below) |
| **Difference** | +11 | +111 | City overstates due to errors |

---

## Side-by-Side Comparison

### Our Table A (6 Projects, 745 Units)

| # | Address | APN | Units | VLI | Status | App Complete | Notes |
|---|---------|-----|-------|-----|--------|--------------|-------|
| 1 | 2276 SHATTUCK Ave | 057 202800400 | 336 | 0 | In Review | 2025-08-07 | SB330, Density Bonus |
| 2 | 2425 DURANT Ave | 055 187800701 | 117 | 0 | Pending Final | 2025-03-13 | SB330, Density Bonus (corrected from 250) |
| 3 | 2029 UNIVERSITY Ave | 057 205300801 | 240 | 0 | Pending Final | 2025-06-03 | 100% Density Bonus |
| 4 | 2614 TELEGRAPH Ave | 055 183600800 | 32 | 3 | Corrections | 2025-04-30 | Density Bonus |
| 5 | 1740 UNIVERSITY Ave | 056 201102200 | 12 | 0 | Approved | 2025-09-15 | Mixed-use conversion |
| 6 | 2200 FIFTH St | 056 195800301 | 8 | 0 | Withdrawn | 2025-11-24 | Townhouses + R&D |
| | **TOTAL** | | **745** | **3** | | | |

### City Table A (17 Projects, 856 Units)

| # | Address | Units | Status | In Our Data? | Notes |
|---|---------|-------|--------|--------------|-------|
| 1 | 2425 DURANT Ave | 169 | Pending | **YES** | **OVERSTATED by 52 units** (actual: 117) |
| 2 | 2330 DURANT Ave | 68 | Under Review (SMAP) | **NO** | Different project |
| 3 | 2029 UNIVERSITY Ave | 160 | Approved | **PARTIAL** | Phase 1 - see error below |
| 4 | 2029 UNIVERSITY Ave (Phase 2) | 240 | Under Review | **YES** | **DOUBLE-COUNT ERROR** |
| 5 | 2372 ELLSWORTH St | 49 | Under Review | **NO** | Not in our 2025 Table A |
| 6 | 2598 TELEGRAPH Ave | 17 | Approved | **NO** | Not in our 2025 Table A |
| 7 | 2080 ALLSTON Way | 14 | Approved | **NO** | Not in our 2025 Table A |
| 8 | 2740 SAN PABLO Ave | 13 | Approved | **NO** | Not in our 2025 Table A |
| 9 | 1685 SOLANO Ave | 10 | Under Review | **NO** | Not in our 2025 Table A |
| 10 | 1290 SIXTH St | 11 | Under Review | **NO** | Not in our 2025 Table A |
| 11 | 2055 CENTER St | 49 | Approved | **NO** | Not in our 2025 Table A |
| 12 | 3000 SHATTUCK Ave | 50 | Under Review | **NO** | Not in our 2025 Table A |
| 13 | 1701 UNIVERSITY Ave | 35 | Under Review | **NO** | Not in our 2025 Table A |
| 14 | 2118 DWIGHT Way | 7 | Approved (SB 35) | **NO** | SB 35 streamlined |
| 15 | 2312 SAN PABLO Ave | 17 | Approved | **NO** | Not in our 2025 Table A |
| 16 | 1733 UNIVERSITY Ave | 3 | Under Review | **NO** | Small project |
| 17 | 1740 UNIVERSITY Ave | 12 | Approved | **YES** | Match |
| | **TOTAL** | **856** | | | |

---

## Critical Error: 2029 University Ave Double-Count

### The Problem

The City's Table A lists 2029 UNIVERSITY Ave **twice**:

| Entry | Units | Status | Permit Numbers |
|-------|-------|--------|----------------|
| "2029 UNIVERSITY Ave" | 160 | Approved | Unknown |
| "2029 UNIVERSITY Ave (Phase 2)" | 240 | Under Review | ZP2024-0181, ZP2024-0182 |
| **City Total** | **400** | | |

### The Reality

There is only **ONE** project at 2029 UNIVERSITY Ave:
- **Total units:** 240 (not 400)
- **Permit numbers:** ZP2024-0181, ZP2024-0182, PLN2024-0069, PLN2024-0070
- **Status:** Pending Final Action (application complete 2025-06-03)
- **Developer:** Single 23-story, 240-unit building

### Impact

| Metric | City Reported | Actual | Error |
|--------|---------------|--------|-------|
| Units at 2029 University | 400 | 240 | **+160 over-count** |
| Total Table A Units | 755 | 595 | **+160 over-count** |

### Evidence

From Accela permit record ZP2024-0181:
> "The project is the construction of a new 23-story (256'-0"), **240-unit** housing development with 190,878 sf of new residential use and parking garage for up to 29 spaces."

There is no "Phase 1" with 160 units. The City appears to have:
1. Listed an earlier project version (160 units) as a separate entry
2. Also listed the current 240-unit project as "Phase 2"
3. Counted both, inflating the total by 160 units

---

## Critical Error: 2425 Durant Ave Over-Count

### The Problem

The City's Table A reports **169 units** for 2425 DURANT Ave:
- VLI: 6 units
- LI: 7 units
- Mod: 6 units
- Above Mod: 13 + 137 = 150 units
- **City Total: 169 units**

### The Reality

The actual project has **117 units**:
- Permit: ZP2024-0162
- Source: Accela permit description + Gellerman architectural KML
- Building: 20-story, 200-ft tall, 135,750 SF
- Bedrooms: 248 (18 one-bed, 134 two-bed, 96 three-bed)
- **Actual units: 117**

### Impact

| Metric | City Reported | Actual | Error |
|--------|---------------|--------|-------|
| Units at 2425 Durant | 169 | 117 | **+52 over-count** |

---

## Match Analysis

### Projects in BOTH Tables

| Address | Our Units | City Units | Match? | Notes |
|---------|-----------|------------|--------|-------|
| 2425 DURANT Ave | 117 | 169 | **NO** | City overstates by 52 units |
| 2029 UNIVERSITY Ave | 240 | 240 (Phase 2) | Yes | But city also lists phantom 160-unit entry |
| 1740 UNIVERSITY Ave | 12 | 12 | Yes | |

### Projects in Our Table A Only

| Address | Units | Why Not in City Table A? |
|---------|-------|--------------------------|
| 2276 SHATTUCK Ave | 336 | App complete Aug 2025 - may be in different table |
| 2614 TELEGRAPH Ave | 32 | App complete Apr 2025 - may be categorized differently |
| 2200 FIFTH St | 8 | Withdrawn - may be excluded |

### Projects in City Table A Only

| Address | Units | Why Not in Our Table A? |
|---------|-------|-------------------------|
| 2029 UNIVERSITY Ave (160) | 160 | **ERROR** - phantom entry (double-count) |
| 2330 DURANT Ave | 68 | Different project (SMAP) |
| 2372 ELLSWORTH St | 49 | Prior year application |
| 2598 TELEGRAPH Ave | 17 | Prior year entitled |
| 2080 ALLSTON Way | 14 | Prior year entitled |
| 2740 SAN PABLO Ave | 13 | Prior year application |
| 1685 SOLANO Ave | 10 | Prior year application |
| 1290 SIXTH St | 11 | Prior year application |
| 2055 CENTER St | 49 | Prior year entitled |
| 3000 SHATTUCK Ave | 50 | Prior year application |
| 1701 UNIVERSITY Ave | 35 | Prior year application |
| 2118 DWIGHT Way | 7 | SB 35 streamlined |
| 2312 SAN PABLO Ave | 17 | Prior year entitled |
| 1733 UNIVERSITY Ave | 3 | Small project |

---

## Discrepancy Summary

| Issue | Count | Units Affected | Severity |
|-------|-------|----------------|----------|
| **Double-count (2029 University)** | 1 | +160 | **Critical** |
| **Over-count (2425 Durant)** | 1 | +52 | **Critical** |
| **Total City Over-count** | 2 | **+212** | **Critical** |
| Projects in city but not ours | 14 | ~393 | Medium (prior years) |
| Projects in ours but not city | 3 | ~376 | Medium (timing) |

---

## Recommendations

1. **Report 2029 University error to City** - 160 phantom units (double-count)
2. **Report 2425 Durant error to City** - 169 units reported, actual is 117 (+52 over-count)
3. **Clarify Table A scope** - City includes prior-year applications; we include only 2025 completions
4. **Add withdrawn projects** - 2200 Fifth St (8 units) was withdrawn, may explain exclusion

---

*Comparison generated 2026-04-15*
