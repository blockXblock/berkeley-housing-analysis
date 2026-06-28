# C2 Tranche 1 — net_units write (audit record)

**Date:** 2026-06-28
**Who:** CC (Claude Code), gated + confirmed by John (spans verified before the write).
**What:** Set `event_classifications.net_units` on **15** multifamily count-gap `new_unit` masters
(finaled 2018–2025) that had blank/null `UnitsAdded` and were dropped to zero in the v4 CO total.
**Why:** C2 of the four-corrections APR reconciliation (`scratch/2026-06-27/four_corrections_sizing.py`) —
the largest CO lever. These buildings' unit counts are recoverable from the WorkDescription (noun-anchored,
matched-span-verified). This is the first v4 mutation of the reconciliation.

**Layer / discipline:** ADR-002 VERDICT layer — `net_units` overwrite-safe, re-runnable. Only `net_units`
on the finaled master event of each permit was touched; `housing_role`, `is_master`, `events`, and every
permit not listed below were untouched. Single transaction, rowcount==1 per permit (all-or-nothing).

**Source of values:** `scratch/2026-06-28/c2_count_recovery.csv` (recovery-to-review artifact; John verified
every matched span). Tranche-1 filter = pure-dwelling recoveries (no live-work/sleeping → tranche 2;
excludes B2020-03895 → #3 building-identity queue, B2025-03934 → role-review, B2018-03160 → Accela).

**Snapshot (pre-write):** `databases/keep_snapshot_2026-06-28_pre-c2-tranche1.db` (integrity_check `ok`,
size-matched). **Pre-write live v4 sha:** `7ada3278454a65dc` → **post-write:** `28d9d91dfc486f6a`.

## The 15 permits written

| permit | finaled CY | net_units set | method | matched span(s) |
|---|---|---|---|---|
| B2016-03894 | 2018 | 152 | anchored | `152 dwelling unit` |
| B2016-05831 | 2018 | 4 | anchored | `4 unit` |
| B2016-05821 | 2020 | 56 | anchored | `56 dwelling unit` |
| B2017-01855 | 2020 | 170 | compound | `159 dwelling units` + `11 townhomes` |
| B2019-01789 | 2021 | 40 | anchored | `40 Dwelling Units` |
| B2019-01150 | 2021 | 78 | anchored | `78 dwelling units` |
| B2019-05475 | 2022 | 37 | anchored | `37 Dwelling Units` (consistency: 34+1+2=37 ✓) |
| B2016-05125 | 2022 | 107 | anchored | `107 Dwelling units` |
| B2019-02831 | 2023 | 4 | anchored | `4 Unit` |
| B2019-04686 | 2023 | 37 | anchored | `37 unit` |
| B2020-02038 | 2023 | 2 | word | `duplex` |
| B2020-02831 | 2023 | 87 | anchored | `87-dwelling units` |
| B2020-03911 | 2023 | 48 | anchored | `48-dwelling units` |
| B2021-05812 | 2024 | 81 | anchored | `81 dwelling units` |
| B2021-04892 | 2025 | 4 | anchored | `4 unit` |

**Total: 907 units.** Prior `net_units` for all 15 = NULL (captured pre-write).

## Effect (real before/after CO-by-CY, from the mutated DB)

| CY | before | +T1 | after | city | Δ after |
|---|---|---|---|---|---|
| 2018 | 34 | 156 | 190 | 229 | −39 |
| 2019 | 239 | 0 | 239 | 313 | −74 |
| 2020 | 71 | 226 | 297 | 405 | −108 |
| 2021 | 388 | 118 | 506 | 331 | +175 |
| 2022 | 429 | 144 | 573 | 828 | −255 |
| 2023 | 450 | 178 | 628 | 716 | −88 |
| 2024 | 865 | 81 | 946 | 708 | +238 |
| 2025 | 590 | 4 | 594 | 492 | +102 |
| **TOT** | **3066** | **907** | **3973** | **4022** | **−49** |

Cumulative CO gap closed **−956 → −49** (tranche 1 alone). Over-years (2021/2024/2025) to be rebalanced
by C1 relabel (+) and C3 phantom-master / 1951 Shattuck (−163, CY2024).

## Verification trace
- Snapshot integrity `ok`, size-matched. · 15/15 rowcount==1 (committed). · Post-write fresh-connection
  verify: all 15 `net_units == recovered_count`. · Idempotency: re-run changed **0 rows** (no-op).

## Reverse (undo)
Prior state was NULL on all 15. To revert:
```sql
UPDATE event_classifications SET net_units = NULL
WHERE event_id IN (SELECT event_id FROM events
   WHERE source_record_key IN ('B2016-03894','B2016-05831','B2016-05821','B2017-01855','B2019-01789',
     'B2019-01150','B2019-05475','B2016-05125','B2019-02831','B2019-04686','B2020-02038','B2020-02831',
     'B2020-03911','B2021-05812','B2021-04892') AND event_type_code='permit_finaled')
  AND housing_role='new_unit' AND is_master=1;
```
Or restore `databases/keep_snapshot_2026-06-28_pre-c2-tranche1.db` over the live DB.

## NOT in this tranche (queued)
- **Tranche 2** (tagged live-work/sleeping line-items): B2015-06007 (19 live-work), B2019-02824 (4 live-work),
  B2016-03011 (39+2 live-work), B2018-05067 (22+2 live-work), B2021-04949 (40 sleeping + 1 mgr).
- **#3 building-identity queue:** B2020-03895 (entangled, multi-permit HCD-ADU parcel 053-1601-030-00).
- **Role-review:** B2025-03934 (meter permit, units belong to B2024-00824).
- **Accela:** B2018-03160 (mini-dorm, sqft only).

*Not committed to git. v4 mutation only; this record is the audit trail.*
