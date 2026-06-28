# C-multifamily over-collapse — phased-building double-count fix (audit record)

**Date:** 2026-06-28
**Who:** CC, gated + confirmed by John (groupings re-confirmed read-only first; Option A chosen).
**What:** Three phased multifamily buildings were **double-counted** — both the foundation/podium phase AND
the superstructure/completion phase were classified `new_unit` with the whole-building count. Demote each
**foundation/podium phase → subsidiary / net_units 0**, keep the **completion** as the single counted master.
For the group-living building, also restore the manager unit on the completion (Option A). **Net −199 CO.**
**Why:** C-multifamily (OVER side) of the four-corrections reconciliation — the independently-grounded half
(we already hold the count; this fixes our internal double). The UNDER side (+147, three buildings whose
completion permit is `ambiguous` with NO unit count in our text) is **HELD for an Accela pull** — not touched.

## The 3 buildings (keep / demote)
| APN | KEEP (completion, untouched/adjusted) | DEMOTE (foundation/podium → subsidiary/0) | net |
|---|---|---|---|
| 057-2025-013 | **B2022-01111** new_unit/81 ("Phase 2 … all building elements except foundation/podium") | **B2021-05812** ("Phase I – Concrete podium, foundation, levels 1-3") | **−81** |
| 055-1819-001 | **B2019-01950** new_unit/78 ("Phase II: Architectural & Structural Superstructure") | **B2019-01150** ("Phase I: Foundation, concrete podium, underground utilities") | **−78** |
| 056-1928-019 | **B2021-02423** new_unit/**40→41** ("New 4-story group living, 40 sleeping + 1 manager") | **B2021-04949** ("Foundation, grading and shoring phase … Phase II permit is B2021-02423") | **−40** |

**Total −199.** Building counts after: 81, 78, 41 (each counted once).

## ⚠ C2-TRANCHE-2 RECONCILIATION (B2021-04949)
`B2021-04949` (the demoted foundation phase) was the permit **C2-tranche-2 wrote** on 2026-06-28
(`docs/audit/2026-06-28_c2_tranche2_write.md`): it set net_units=41 with `convention_dependent=true
(40 sleeping + 1 manager dwelling)`. That was correct on the COUNT (41) but on the wrong permit — it counted
the **foundation phase** of a building whose **completion** permit (B2021-02423) was ALSO counted (40),
creating an 81-unit double. This write **reconciles that**:
- B2021-04949 (foundation) → subsidiary / net_units 0 (reverses C2-T2's +41 on this permit).
- B2021-02423 (completion) → net_units **40 → 41**, with the **convention_dependent flag re-homed** onto it
  (the manager-unit + live/sleeping convention is preserved, now on the correct completion permit).
- Net for the building: 81 → 41 (the real group-living count, manager unit intact).

So C2-T2's substance (41 units, convention-flagged) survives — moved from the foundation phase to the
completion. The C2 cumulative is unchanged in spirit (this building still counts 41, just once, on the right permit).

## HELD contested-direction note — 056-1928-019 vs city
City credits **0** CO on 056-1928-019 (no city completion yet, or credited elsewhere). After this collapse we
count **41** there → we are **+41 over the city** on this building. **This is a HELD item, not resolved here** —
the collapse only fixes OUR internal double-count (81→41); whether the city is under (hasn't CO'd a real
41-unit building) or we are over (finaled-but-not-city-recognized) is part of the open residual/contested
investigation and requires independent (Accela/CofO) proof, not a mirror comparison.

## Layer / discipline
ADR-002 VERDICT layer; housing_role + net_units changes. Only the 3 foundation phases (→subsidiary/0) and
the 1 completion bump (40→41) touched; the 2 kept completions (B2022-01111, B2019-01950) untouched; **PROTECT
set EXCLUDED** (056-1945-007-04 Buildings B&C = 8 real units; 052-1516-024 SFR 1/2/3 = 3 real houses). Single
transaction, rowcount==1 per change, all-or-nothing, **protection guard** (every demote target verified
foundation/podium/grading — guard PASS, 0 halts).

**Snapshot (pre-write):** `databases/keep_snapshot_2026-06-28_pre-c-multifamily.db` (integrity `ok`, size-matched).
**sha:** pre `cd88b5f5a417864d` → post **`9cb9471658e13281`**.

## Verification trace
- Pre-write fingerprint: all 6 permits confirmed new_unit/master (demotes 81/78/41, keeps 81/78, bump 40).
- Protection guard PASS (3/3 demote targets foundation/podium/grading).
- STEP 3: 4/4 rowcount==1 → COMMITTED. STEP 4 (fresh conn): 3 demotes → subsidiary/0, 2 keeps still new_unit
  81/78, bump B2021-02423 → new_unit/41 → PASS. STEP 5 idempotency: re-run changed **0 rows**.
- STEP 6 real before/after:

| CY | before | +C | after | city | Δ after |
|---|---|---|---|---|---|
| 2021 | 505 | −78 | 427 | 331 | +96 |
| 2024 | 821 | −122 | 699 | 708 | −9 |
| 2025 | 588 | +1 | 589 | 492 | +97 |
| **TOT** | **3922** | **−199** | **3723** | **4022** | **−299** |

## Reconciliation state (intermediate — OVER done, UNDER held)
```
3,066 baseline + C2 +1,036 − C3 Shattuck −163 − C3 ADU-tail −17 − C-multifamily −199 = 3,723 vs city 4,022 (−299)
```
**Expected:** the OVER-collapse alone *deepens* the gap (−100 → −299) because it removes real pipeline
double-counts the city never had. The **HELD UNDER side (+147, the 3 ambiguous-completion buildings) would
bring it to ~3,870 (−152)** once an Accela pull supplies their independent unit counts. The residual ~−150
is the genuine under-count / contested-direction question (real housing the city counts that we don't),
needing per-permit independent proof — not assertable from the mirror.

## Reverse (undo)
Restore `databases/keep_snapshot_2026-06-28_pre-c-multifamily.db`, or:
```sql
UPDATE event_classifications SET housing_role='new_unit', net_units=81 WHERE event_id IN (SELECT event_id FROM events WHERE source_record_key='B2021-05812' AND event_type_code='permit_finaled') AND is_master=1;
UPDATE event_classifications SET housing_role='new_unit', net_units=78 WHERE event_id IN (SELECT event_id FROM events WHERE source_record_key='B2019-01150' AND event_type_code='permit_finaled') AND is_master=1;
UPDATE event_classifications SET housing_role='new_unit', net_units=41 WHERE event_id IN (SELECT event_id FROM events WHERE source_record_key='B2021-04949' AND event_type_code='permit_finaled') AND is_master=1;  -- restores C2-T2 state
UPDATE event_classifications SET net_units=40 WHERE event_id IN (SELECT event_id FROM events WHERE source_record_key='B2021-02423' AND event_type_code='permit_finaled') AND is_master=1;  -- (basis_note annotations cosmetic; snapshot restore reverts fully)
```

*Not committed to git. v4 mutation only; this record is the audit trail.*
