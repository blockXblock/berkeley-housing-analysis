# CPRA Import Results — 2026-05-11

**Import completed:** 2026-05-11 20:12:51
**Status:** COMMITTED

---

## 1. Summary Counts

| Metric | Count |
|--------|-------|
| Total CPRA permits processed | 10,873 |
| Permits matched to existing projects | 122 |
| New R-2 projects created | 2 |
| Total permits inserted | 124 |
| Permits skipped (false positives) | 3 |
| Errors | 0 |

### Skip List (§16)
- B2025-03731: Water heater stand (inflated unit count)
- B2024-05284: Wood post repair (inflated unit count)
- B2024-04593: Reroof (inflated unit count)

### Exclusions (§17)
- Project 93 (1312 ADDISON St): Excluded from fuzzy matching (APN/address issues)

---

## 2. Post-Import Database Counts

| Table | Count | Expected | Status |
|-------|-------|----------|--------|
| permits | 242 | 242 | ✓ |
| projects | 181 | 181 | ✓ |
| project_events | 2,733 | ~2,700+ | ✓ |
| project_parcels | 177 | — | ✓ |
| FK violations | 0 | 0 | ✓ |

---

## 3. Top 20 Projects by CPRA Permits Added

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
| 93 | 1312 ADDISON St | 3 |
| 88 | 705 ARLINGTON Ave | 3 |
| 79 | 1111 ALLSTON Way | 3 |
| 53 | 2641 COLLEGE Ave | 3 |

---

## 4. Sample of 10 Newly Inserted Permits

| ID | Project | Permit # | Type | Status | Issued | Valuation |
|----|---------|----------|------|--------|--------|-----------|
| 242 | 184 | B2025-00168 | Building Permit | Issued | 2025-07-30 | — |
| 241 | 183 | B2022-05957 | Building Permit | Issued | 2024-09-05 | — |
| 240 | 71 | B2025-03189 | Building Permit | Issued | 2025-08-25 | $6,245 |
| 239 | 71 | B2025-00897 | Building Permit | Issued | 2025-03-10 | $8,228 |
| 238 | 83 | B2025-02220 | Building Permit | Issued | 2025-07-23 | $0 |
| 237 | 83 | B2024-03997 | Building Permit | Issued | 2024-08-14 | $500 |
| 236 | 83 | B2024-02712 | Building Permit | Issued | 2024-08-07 | $10,000 |
| 235 | 83 | B2024-02570 | Demolition Permit | Issued | 2024-09-27 | $550,000 |
| 234 | 83 | B2024-02569 | Demolition Permit | Issued | 2024-09-25 | $10,000 |
| 233 | 83 | B2022-03783 | Building Permit | Issued | 2023-01-11 | $375,000 |

---

## 5. Staleness Assessment Delta

| Classification | Pre-Import | Post-Import | Change |
|----------------|------------|-------------|--------|
| UP_TO_DATE | 34 | 60 | +26 |
| STALE | 33 | 1 | -32 |
| UNMATCHED | 112 | 115 | +3 |

**Key improvement:** 32 projects moved from STALE to UP_TO_DATE after import.

### Top 5 Projects Now UP_TO_DATE

| Project | Address | CPRA Permits |
|---------|---------|--------------|
| 70 | 3001 BENVENUE Ave | 1 |
| 92 | 3036 REGENT St | 2 |
| 150 | 3030 TELEGRAPH Ave | 4 |
| 154 | 2001 ASHBY Ave | 1 |
| 143 | 2902 ADELINE St | 3 |

---

## 6. New Projects Created

| ID | Name | Address |
|----|------|---------|
| 180 | nan | 2065 Kittredge St |
| 181 | nan | 2015 Blake St |
| 182 | nan | 2072 Addison St |
| 183 | 2328 CHANNING Way | 2328 CHANNING Way |
| 184 | 2330 BLAKE St | 2330 BLAKE St |

---

## 7. Anomalies

**None detected.**

---

## 8. Backup Information

- **Pre-import backup:** `databases/berkeley_housing_v2_pre_cpra_import_2026-05-11.db`
- **Import log:** `scripts/migration/logs/cpra_import_2026-05-11_live.log`
- **Summary:** `scripts/migration/logs/cpra_import_2026-05-11_summary.md`

---

*Generated 2026-05-11 20:12:51*
