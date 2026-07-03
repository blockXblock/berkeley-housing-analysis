# The no-candidate batch — the reconciliation's last 20 rows, all adjudicated (0 unmatched)

**Date:** 2026-07-03 · **Who:** background agent (full playbook) + CC write-gate verification + John's
go (with the Hearst amendment) · **Snapshot:** `keep_snapshot_2026-07-03_pre-nocandidate.db` ·
CO 4,212 → **4,229** (+17 net); baseline **2026-07-03i**; chain re-validated (incl. one deliberate
C2-checksum update the gate correctly forced — see below). Worknotes:
`scratch/2026-07-03/no_candidate_worknotes.md`; verdicts in the agent transcript + ledger rows 175-190.

## Outcome: 25 uncovered units = 17 recall (net) + 8 city-error — NOTHING unmatched
**Recalls applied (14 promotions + 2 upgrades):** dominated by the **UnitsAdded=0/None trap** — nine
genuinely unit-creating permits (JADU conversions, ADU builds, legalizations, "reconfigure to two
units") carry a zero/blank UnitsAdded. Others: the base-vs-revision **address split** (the 1024
Grizzly Peak duplex — REVs said "0 Grizzly Peak"), the second **Grayson duplex** twin, a mini-dorm,
the 1734 Spruce **legalization** under the row's second APN. **The Hearst amendment** (John-approved):
`apply_grounded_counts` may UPGRADE a counted value upward when the stored count came from the derive
rule's blank-count floor AND the permit's own raw NumberUnits corroborates exactly — applied to the
twin 1173 Hearst duplexes (1→2 each) and, unexpectedly, to 1030 Grayson (pre-counted at 1 → 2).
**Write-gate diff corrections (the verify-everything dividend):** 1030 Grayson was pre-counted at 1
(upgrade net +1, not +2); **770 Page was already counted under its re-platted child APN** — the
agent's "recall" was a matching artifact; the method annotated without change (+0). Projected +19
became actual **+17**, and the diff explains every unit.
**B2020-03895 resolved (the June-28 c2_excluded "#3 pending case"):** grounded at 2 from its own
description+REV01. **THE ENTIRE HELD FILE IS NOW EMPTY** (held_147 AND c2_excluded). Resolving it
moved B2020-03895 into C2-T1's flow — the chain's checksum gate HALTED the rebuild until the
calibration was deliberately updated (15/907 → 16/909); both C2 and the ledger set the same 2
idempotently.

## FIVE new city-error classes (8 units) — Audit-page material, each with receipts
1. **"CO" dated at the permit's ISSUANCE** (1811 Sixty-Third: credited CY2020 at 2020-01-28 = the
   issuance date, then again CY2021 at the real final — same 2 units twice; parcel real 3, city 5).
2. **Utility-meter re-credit** (2619 College: "add 2 new meters for ADUs… REF B2024-00819" credited
   the referenced, already-counted ADUs a second time — the row even carries the real permit's final date).
3. **Zoning approval credited as a CO** (1284 Hearst: ZP2019-0022 in the tracking field; the same
   shed-ADU credited again at its actual 2021 BP final).
4. **Cross-CY duplicate** (1825 Berkeley: B2022-02049 credited in CY2023 AND CY2024).
5. **Non-dwelling credited as SFD** (2434 McGee: a 448 SF garage-and-workshop, OccType=U, credited as
   a single-family dwelling; the complete Accela record set contains no unit-creating permit).

## The reconciliation's terminal state
**Ours 4,229 vs adjudicated city 4,099 = +130 — every unit in BOTH directions carries a named verdict.**
Ours-more: the city's own gaps (unfiled GLA CO 41; Den under-read/CKAN-drop; the UnitsAdded=0 recall
class they caught and we now match; legalizations their state copy dropped). City-more: their five
error classes (8u) + designation-counting we don't follow. Zero unexamined rows remain anywhere.

## Detector to encode (follow-up): the re-credit tells are mechanical
CO_ISSUE_DT1 == the permit's issuance date; a tracking id that is a ZP or a meter/utility permit
referencing another permit; the same tracking id credited in two CYs — all machine-checkable in the
mirror. Natural JN-G companions.
