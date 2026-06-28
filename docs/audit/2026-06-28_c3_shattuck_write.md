# C3 Shattuck — phantom-master collapse (audit record)

**Date:** 2026-06-28
**Who:** CC, gated + confirmed by John (premise verified read-only first: `scratch/2026-06-28/c3_premise_check.py`).
**What:** Collapse the **two phase-permits of ONE building** on APN `057-2046-001-00` (1951 Shattuck) that were
each counted as 163 units (326 total). Reclassify **Phase 2** to `subsidiary` + `net_units=0`, keeping **Phase 1**
as the single counted `new_unit` master. Net effect: **−163 CO** (the building is counted once, not twice).
**Why:** C3 of the four-corrections APR reconciliation — phantom-master double-count.

## The building-identity finding (one building, two phases)
| permit | role (before→after) | net_units (before→after) | finaled | WorkDescription |
|---|---|---|---|---|
| **B2019-05608 (Phase 1) — MASTER, KEPT** | new_unit (unchanged) | 163 (unchanged) | CY2024 | *"Phase 1 of 2 consists of the Basement and first floor of a new building. New mixed-use building: approx. 179,680 GSF, 12 story residential building with 163 rental units and ground floor retail."* |
| **B2021-04893 (Phase 2) — COLLAPSED** | new_unit → **subsidiary** | 163 → **0** | CY2024 | *"Phase 2: Consists of levels 2-12 of new construction approx 179,680 GSF, 12 story residential building with 163 rental units and ground floor retail."* |

**Relationship recorded: B2021-04893 (Phase 2) is SUBSIDIARY TO master B2019-05608 (Phase 1) — they are one
163-unit, 12-story, 179,680-GSF building built in two phases (Phase 1 = basement+L1; Phase 2 = L2–12).** The
"163 rental units" on each permit is the *whole-building* count, not per-phase.

**Corroboration (why 163, not 326):** identical GSF (179,680) and story count (12) on both permits;
`B2021-04893-REV14` = *"Revising sheet to reflect correct number of units **(163)**"*; `REV04` = *"all **163**
unit entry doors"*; `B2021-05057` (grading/shoring) = *"Phase I of II … under B2019-05608, Phase II of II …
under B2021-04893"* (explicitly one project). The ~26 DEF/REV children were already `subsidiary`/0 (untouched).

## Layer / discipline
ADR-002 VERDICT layer. **housing_role change** (heavier than C2's net_units-only). Only Phase 2's finaled
master event touched (`housing_role`→subsidiary, `net_units`→0); Phase 1 and all other permits untouched.
Single transaction, rowcount==1, all-or-nothing.

**Snapshot (pre-write):** `databases/keep_snapshot_2026-06-28_pre-c3-shattuck.db` (integrity `ok`, size-matched).
**sha:** pre `d7f147ec6888b30f` → post **`12a7d7440128e8e3`**.

## Verification trace
- Premise re-confirmed at write time: Phase 2 = new_unit/master/net_units=163/CY2024; Phase 1 = new_unit/163;
  exactly 1 target row.
- STEP 3: rowcount==1 → COMMITTED. STEP 4 (fresh conn): Phase 2 now subsidiary/0, Phase 1 still new_unit/163 → PASS.
- STEP 5 idempotency: re-run changed **0 rows** (Phase 2 no longer a new_unit master). 
- STEP 6 real before/after:

| CY | before | +C3 | after | city | Δ after |
|---|---|---|---|---|---|
| 2024 | 987 | **−163** | **824** | 708 | +116 |
| **TOT** | **4102** | **−163** | **3939** | **4022** | **−83** |

CY2024 dropped by exactly **−163** (987→824). Cumulative CO **+80 → −83** vs city 4,022, as predicted.
(Note: the original "946→783" projection was pre-C2; the real pre-C3 CY2024 is 987 because C2 tranche-2's
live-work permit B2021-04949 added 41 to 2024. The Δ−163 and cumulative −83 match exactly.)

## Reverse (undo)
Restore `databases/keep_snapshot_2026-06-28_pre-c3-shattuck.db`, or:
```sql
UPDATE event_classifications SET housing_role='new_unit', net_units=163
WHERE event_id IN (SELECT event_id FROM events WHERE source_record_key='B2021-04893'
   AND event_type_code='permit_finaled') AND is_master=1;
```

## Status of C3 after this write
- **Shattuck −163: DONE** (this write).
- **ADU-pair tail: NOT done** — ~25 candidate ancillary double-counts (solar/meter permits mis-counted as
  new_unit=1 on ADU parcels) among the 49 multi-permit ADU parcels; 2 genuine pairs to PROTECT, 6 to review.
  Needs its own per-permit review CSV before any write (entangled with the C1-phantom set). See
  `scratch/2026-06-28/c3_premise_check.py`.

## Reconciliation now
3,066 baseline + C2 +1,036 (DONE) − C3 Shattuck −163 (DONE) = **3,939 vs city 4,022 (−83)**. C4 (BP timing)
and the C3 ADU-tail remain.

*Not committed to git. v4 mutation only; this record is the audit trail.*
