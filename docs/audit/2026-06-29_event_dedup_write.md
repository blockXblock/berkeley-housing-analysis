# In-place event-dedup — collapse cross-file duplicate milestone events (audit record)

**Date:** 2026-06-29 · **Who:** CC, gated + confirmed by John. · **NOT a re-ingest** (all manual classification preserved).
**What:** The CPRA two-file overlap (1,430 shared permits) + within-file dup rows made each overlap permit emit
its milestone events **twice** (JN-A ingestion deduped permit KEYS but, per its own cell-26 note, "DUPLICATE
source_record_key (cross-file overlap - REPORTED, not resolved)"). This collapses same-`(permit, milestone,
date)` duplicate events to ONE (keep `MIN(event_id)`), deleting the duplicate event + its 1:1 classification.
**2,870 duplicate events removed; CO UNCHANGED (3,676).**

## FK surface (why re-point was trivial)
`event_classifications` is **1:1** with `events` (both 82,923 post-write). The other 3 event_id tables
(`classification_decisions`, `structure_events`, `actor_actions`) are **empty**. So "re-point" = the kept event
already carries its own classification; we delete the duplicate's event+classification. **No orphans, no lost
coverage** — verified 0 orphaned classifications post-write.

## The 3 tiers (Step B risk design)
**TIER 1 — AUTO-COLLAPSE (2,870 events):** same `(permit, milestone, date)`, classifications agree, substantive
fields (WorkDescription/UnitsAdded/NumberUnits) agree → keep MIN, delete the dup. Mostly submitted/issued
(verified 0 manual corrections); the safe finaled pairs are uniform alteration/subsidiary.

**TIER 2 — REVIEW-HOLD (3 groups, untouched):** a guard held any group where the two events' substantive fields
OR classifications disagree (protects manual corrections from keep-MIN):
- `B2014-05786` finaled 2021-08-31 — classifications differ (new_unit/44 vs **dedup47's** subsidiary/0). Held so
  the dedup47 correction isn't dropped; CO already neutral (the subsidiary contributes 0). *Cosmetic dup only.*
- `B2022-00032` issued 2022-10-04 **and** submitted 2022-01-04 — **WorkDescription differs between the two files**
  (the genuine substantive-differ case). Not collapsed — needs John's eye on which description is canonical.

**TIER 3 — DIFFERENT-DATE finaled (12 groups, listed not touched):** same permit+milestone, **different finaled
dates** across the two files → the `(permit,milestone,date)` key cannot catch these, and a different finaled date
may be a **legit re-final**, not a dup. Flagged for review:
`B2018-03576, B2019-01241, B2020-03494` (CO already deduped via dedup47), `B2021-00008-DEF01/DEF04/REV03/REV06/
REV09/REV10/REV11` (REV/DEF subs, subsidiary), `B2022-00426, B2022-03754`.

## Verification trace
- Snapshot `databases/keep_snapshot_2026-06-29_pre-event-dedup.db` (integrity ok, size-matched).
- Guarded write (all-or-nothing): deleted **2,870** classifications + **2,870** events (== to_remove); **0 orphaned
  classifications**; **0 dup-groups lost all events**; **CO 3,676 → 3,676 (unchanged)** → guards PASS, COMMITTED.
- Fresh-conn verify: events **85,793 → 82,923 (−2,870)**; classifications 82,923 == events (1:1 intact); CO 3,676;
  **30,764 distinct permits retained (none lost)**.
- Idempotency: remaining same-date dup groups = **3** (exactly the held tier-2).
- **sha:** pre `899993e290e06717` → post **`6389e612ac0c6b04`**.

## BONUS — BP count at PERMIT level (Step B flagged event-inflation)
- `permit_issued`: **event-level (post-dedup) 30,512** · **PERMIT-level (distinct) 30,511** · pre-dedup
  event-level ≈ **31,941**. So the all-time issued count was event-inflated by ~1,430 (the overlap).
- The reconciliation's **BP 4,911** is a *filtered subset* (not all-time), so it must be re-confirmed to count
  **distinct permits**, not events. The dedup removes the inflation risk regardless; **recommend the BP-side
  reconciliation explicitly use `COUNT(DISTINCT source_record_key)`.**

## Reverse
Restore `keep_snapshot_2026-06-29_pre-event-dedup.db` (full revert of all 2,870 deletions).

*Not committed to git. v4 mutation only (structural, CO-neutral); this record is the durable trail.*
