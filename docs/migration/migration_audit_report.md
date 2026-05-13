# Migration Audit Report: v1 → v2

**Generated:** 2026-05-07T16:38:14.449895
**Asserted By:** migration_v1_to_v2_20260507

---

## 1. Count Deltas

| Metric | v1 | v2 | Delta | Notes |
|--------|---:|---:|------:|-------|
| projects | 179 | 179 | +0 |  |
| units | 14070 | 14071 | +1 | -1 → 0 fix |
| vli_units | 968 | 968 | +0 |  |
| permits | 114 | 118 | +4 | project_permits + building_permits |
| events | 2306 | 2611 | +305 | date columns + permit_events |
| documents | 1423 | 1406 | -17 | 17 quarantined |

## 2. Synthetic Events Created

**Total:** 1 synthetic entitlement events

| Project ID | Event Date | Event Type | Reason |
|------------|------------|------------|--------|
| 179 | 2018 | entitlement_approved | entitled date existed but no entitlement_approved event |

## 3. Duplicate Address Review Cases

**Total:** 3 duplicate address pairs

| Address | Project 1 | Project 2 | P1 Units | P2 Units | P1 Status | P2 Status | P1 Permits | P2 Permits |
|---------|-----------|-----------|----------|----------|-----------|-----------|------------|------------|
| 2138 KITTREDGE St | 113 | 118 | 73 | 66 | Amendment Pending | Entitled | ZP2026-0006 | ZP2024-0114 |
| 2455 TELEGRAPH Ave | 25 | 115 | 68 | 68 | Under Review | Under Review | PLN2025-0066 | ZP2026-0015 |
| 2740 SHASTA Rd | 86 | 109 | 0 | 0 | Incomplete Pending Applicant | Corrections Pending Applicant | ZP2022-0091 | ZP2025-0100 |

## 4. Orphan Documents Quarantined

**Total:** 17 documents quarantined

| Document ID | Original Project ID | Title | Reason |
|-------------|---------------------|-------|--------|
| 1407 | 48 | 2024-03-29 Incomplete LTR 2317 Channing  | project_id not found in v2 |
| 1408 | 48 | 2024-04-18 Complete LTR 2317 Channing | project_id not found in v2 |
| 1409 | 48 | 2024-03-12 APP PCKT 2317 Channing | project_id not found in v2 |
| 1410 | 48 | 2024-05-16 Application Processing Status | project_id not found in v2 |
| 1411 | 48 | 2024-07-02 RESUB 2317 Channing | project_id not found in v2 |
| 1412 | 48 | 2024-07-30 Application Processing Status | project_id not found in v2 |
| 1413 | 48 | 2024-07-30 Application Processing Status | project_id not found in v2 |
| 1414 | 48 | 2024-08-21 RESUB 2317 Channing | project_id not found in v2 |
| 1415 | 48 | 2024-09-21 RESUB 2317 Channing | project_id not found in v2 |
| 1416 | 48 | 2024-09-30 Application Processing Status | project_id not found in v2 |
| 1417 | 48 | 2024-12-30 ZAB POS 2317 Channing | project_id not found in v2 |
| 1418 | 48 | 2024-12-30 ZAB NOD 2317 Channing | project_id not found in v2 |
| 1419 | 48 | 2025-01-21 LTR Cover 2317 Channing | project_id not found in v2 |
| 1420 | 48 | 2025-01-21 UP 2317 Channing | project_id not found in v2 |
| 1421 | 48 | 2024-09-24 AHCP 2317 Channing | project_id not found in v2 |
| 1422 | 48 | 2024-09-24 RESUB 2317 Channing | project_id not found in v2 |
| 1423 | 48 | 2025-01-29 CEQA NOE Filing 2317 Channing | project_id not found in v2 |

## 5. Low Confidence / Inferred Rows

| Table | Count | Notes |
|-------|------:|-------|
| project_events | 1 | Synthetic/inferred data |

## 6. Classifications / Tags Added

| Classification | Label | Count |
|----------------|-------|------:|
| density_bonus | Density Bonus | 55 |
| sb330_protected | SB330 Protected | 17 |
| uc_project | UC Project | 4 |
| ab2011_approved | AB2011 Approved | 2 |
| sb35_approved | SB35 Approved | 2 |

## 7. Reconciliation Notes

- Permits: 107 from project_permits + 11 from building_permits = 118 total
- Project 84: units -1 → 0 (negative value corrected)
- Events: 339 from date columns + 2271 from permit_events = 2610 total

### Unit Delta (+1) Explanation

The +1 unit delta is due to one project having -1 units in the source data, which was corrected to 0 during migration (schema constraint: total_units >= 0).

### Event Count Increase Explanation

Events in v2 come from two sources:
1. **Date columns** (filed, complete, entitled, bp_issued, co_date, etc.)
2. **permit_events table** (legacy event log)

This combined approach captures more events than the v1 permit_events table alone.

### Permit Count Increase Explanation

Permits in v2 come from two sources:
1. **project_permits table**
2. **building_permits table** (supplemental permits not in project_permits)

---

*Report generated 2026-05-07T16:38:14.449895*
