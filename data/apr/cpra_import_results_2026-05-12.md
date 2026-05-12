# CPRA Import Results — 2026-05-12

**Import completed:** 2026-05-12
**Status:** COMMITTED

---

## 1. Summary Counts

| Metric | Count |
|--------|-------|
| Total CPRA permits processed | 10,873 |
| Permits matched to existing projects | 119 |
| New R-2 projects created | 2 |
| Total permits inserted | 121 |
| Permits skipped (false positives) | 3 |
| Project 93 exclusions (APN + fuzzy) | 4 |
| Errors | 0 |

### Skip List (§16)
- B2025-03731: Water heater stand (inflated unit count)
- B2024-05284: Wood post repair (inflated unit count)
- B2024-04593: Reroof (inflated unit count)

### Exclusions (§17)
- Project 93 (1312 ADDISON St): Excluded from ALL matching (APN and fuzzy)
  - 3 permits at 2200 Acton blocked via APN match
  - 1 permit blocked via fuzzy match

---

## 2. Post-Import Database Counts

| Table | Count | Expected | Status |
|-------|-------|----------|--------|
| permits | 239 | 239 | ✓ |
| projects | 181 | 181 | ✓ |
| project_events | 2,787 | ~2,787 | ✓ |
| project_parcels | 177 | — | ✓ |
| FK violations | 0 | 0 | ✓ |
| Permit duplicates | 0 | 0 | ✓ |

---

## 3. Finaled Date Validation

| Metric | Count |
|--------|-------|
| CPRA permits with finaled_date | 55 |
| co_issued events created | 55 |
| Validation threshold | 80% |
| Actual ratio | 100% |
| Status | ✓ PASS |

---

## 4. Top 20 Projects by CPRA Permits Added

| Project ID | Address | Permits |
|------------|---------|---------|
| 83 | 1136 KEITH Ave | 6 |
| 63 | 1716 SEVENTH St | 6 |
| 176 | 2440 SHATTUCK Ave | 5 |
| 174 | 1773 OXFORD St | 4 |
| 157 | 2587 TELEGRAPH Ave | 4 |
| 152 | 1598 UNIVERSITY Ave | 4 |
| 150 | 3030 TELEGRAPH Ave | 4 |
| 139 | 2538 DURANT Ave | 4 |
| 90 | 576 SAN LUIS Rd | 4 |
| 172 | 2650 TELEGRAPH Ave | 3 |
| 159 | 2403 SAN PABLO Ave | 3 |
| 147 | 2300 ELLSWORTH St | 3 |
| 143 | 2902 ADELINE St | 3 |
| 134 | 2480 Bancroft Way | 3 |
| 131 | 811 Cedar | 3 |
| 129 | 1614 Sixth St | 3 |
| 88 | 705 ARLINGTON Ave | 3 |
| 79 | 1111 ALLSTON Way | 3 |
| 53 | 2641 COLLEGE Ave | 3 |
| 173 | 2000 DWIGHT Way | 2 |

---

## 5. Sample of 10 Newly Inserted Permits

| ID | Project | Permit # | Type | Status | Issued | Valuation |
|----|---------|----------|------|--------|--------|-----------|
| 239 | 184 | B2025-00168 | Building Permit | Issued | 2025-07-30 | — |
| 238 | 183 | B2022-05957 | Building Permit | Issued | 2024-09-05 | — |
| 237 | 71 | B2025-03189 | Building Permit | Finaled | 2025-08-25 | $6,245 |
| 236 | 71 | B2025-00897 | Building Permit | Finaled | 2025-03-10 | $8,228 |
| 235 | 83 | B2025-02220 | Building Permit | Finaled | 2025-07-23 | $0 |
| 234 | 83 | B2024-03997 | Building Permit | Issued | 2024-08-14 | $500 |
| 233 | 83 | B2024-02712 | Building Permit | Finaled | 2024-08-07 | $10,000 |
| 232 | 83 | B2024-02570 | Demolition Permit | Finaled | 2024-09-27 | $550,000 |
| 231 | 83 | B2024-02569 | Demolition Permit | Finaled | 2024-09-25 | $10,000 |
| 230 | 83 | B2022-03783 | Building Permit | Issued | 2023-01-11 | $375,000 |

---

## 6. Sample 5 Permits with finaled_date

| ID | Project | Permit # | Type | Issued | Finaled | Address |
|----|---------|----------|------|--------|---------|---------|
| 237 | 71 | B2025-03189 | Building Permit | 2025-08-25 | 2025-09-29 | 40 HILL Rd |
| 236 | 71 | B2025-00897 | Building Permit | 2025-03-10 | 2025-05-09 | 40 HILL Rd |
| 235 | 83 | B2025-02220 | Building Permit | 2025-07-23 | 2025-10-14 | 1136 KEITH Ave |
| 233 | 83 | B2024-02712 | Building Permit | 2024-08-07 | 2025-08-20 | 1136 KEITH Ave |
| 232 | 83 | B2024-02570 | Demolition Permit | 2024-09-27 | 2025-11-10 | 1136 KEITH Ave |

---

## 7. Staleness Assessment

| Classification | Count | Percentage |
|----------------|-------|------------|
| UP_TO_DATE | 29 | 16.0% |
| STALE | 27 | 14.9% |
| UNMATCHED | 125 | 69.1% |

**Methodology:** Cutoff = 12 months (May 12, 2025)
- UP_TO_DATE: Project has CPRA permit issued within last 12 months
- STALE: Project has CPRA permits but all older than 12 months
- UNMATCHED: No CPRA permits linked to project

**Note:** This methodology differs from yesterday's `v1_staleness_assessment_2026-05-10.csv`, which used "before/after v1 event date" criteria rather than "within 12 months of today." Therefore the before/after numbers (yesterday 33 STALE → today 27) are **not directly comparable**. For meaningful before/after comparison, re-run yesterday's methodology against current v2 state.

---

## 8. New Projects Created (by this import)

| ID | Name | Address |
|----|------|---------|
| 183 | 2328 CHANNING Way | 2328 CHANNING Way |
| 184 | 2330 BLAKE St | 2330 BLAKE St |

### Pre-existing v2 projects (unrelated to this import)

Projects 180–182 existed in v2 before this import (created 2026-05-03 by earlier work):

| ID | Address |
|----|---------|
| 180 | 2065 Kittredge St |
| 181 | 2015 Blake St |
| 182 | 2072 Addison St |

---

## 9. Anomalies

- **Staleness methodology changed:** The staleness methodology in §7 differs from yesterday's `v1_staleness_assessment_2026-05-10.csv`. Before/after deltas are not directly comparable until both are re-run with consistent methodology.

---

## 10. Backup Information

- **Pre-import backup:** `databases/berkeley_housing_v2_pre_cpra_import_2026-05-11.db`
- **Import log:** `scripts/migration/logs/cpra_import_2026-05-11_live.log`
- **Summary:** `scripts/migration/logs/cpra_import_2026-05-11_summary.md`

---

*Generated 2026-05-12*
