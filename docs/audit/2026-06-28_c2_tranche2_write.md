# C2 Tranche 2 — net_units write (convention-dependent live-work / sleeping units)

**Date:** 2026-06-28
**Who:** CC, gated + confirmed by John (B2021-04949 = 41 confirmed; spans verified).
**What:** Set `event_classifications.net_units` on **5** `new_unit` masters whose recovered count includes
**live-work and/or sleeping units** — categories the city may count differently in the APR. Each is marked
with a **single flag `convention_dependent=true`** (NOT a per-portion split) so the counted units are
identifiable for reconciliation. Total **129 units**.
**Why:** C2 tranche 2 of the four-corrections APR reconciliation. Separated from tranche 1 (pure dwelling)
because the count convention is policy-dependent; flagging keeps them a visible, subtractable line-item.

**Flag mechanism (no schema change):** `event_classifications` has no boolean column, so the flag is
**appended to the existing `basis_note`** (classifier note preserved): `… | C2-T2 convention_dependent=true
(<split>; src c2_count_recovery.csv)`. Query: `WHERE basis_note LIKE '%convention_dependent=true%'`.
One hop from the flag to the exact subtractable amounts → `scratch/2026-06-28/c2_count_recovery.csv`.

**Layer / discipline:** ADR-002 VERDICT layer (`net_units` overwrite-safe) + a provenance annotation on
`basis_note`. Only these 5 finaled master events touched; `housing_role`, `is_master`, `events`, and every
other permit untouched. Single transaction, rowcount==1 per permit (all-or-nothing).

**Snapshot (pre-write):** `databases/keep_snapshot_2026-06-28_pre-c2-tranche2.db` (integrity `ok`,
size-matched). **sha:** pre `28d9d91dfc486f6a` → post **`d7f147ec6888b30f`** (post-tranche-1 was `28d9d91d`).

## The 5 permits written (flag = convention_dependent=true on each)

| permit | finaled CY | net_units | numeric split | convention | matched span(s) |
|---|---|---|---|---|---|
| B2015-06007 | 2019 | 19 | 19 | live_work | `19 LIVE/WORK UNITS` |
| B2019-02824 | 2022 | 4 | 4 | live_work | `4 Live-Work units` |
| B2016-03011 | 2020 | 41 | 39 + 2 | dwelling + live_work | `39 dwelling units` \| `two live-work units` |
| B2018-05067 | 2022 | 24 | 22 + 2 | dwelling + live_work | `22 dwelling units` \| `2- live-work` |
| B2021-04949 | 2024 | 41 | 40 + 1 | sleeping + manager dwelling | `40 sleeping units` \| `one manager's dwelling unit` |

**Total: 129 units.** Prior `net_units` for all 5 = NULL; prior `basis_note` = "New + housing indicator"
(preserved, flag appended). **Exact subtractable amounts** (if the city excludes a convention): the split
column above and the `count_convention`/`matched_spans` columns in `c2_count_recovery.csv`.

## Effect (real before/after CO-by-CY, post-tranche-1 → post-tranche-2)

| CY | post-T1 | +T2 | post-T2 | city | Δ after |
|---|---|---|---|---|---|
| 2018 | 190 | 0 | 190 | 229 | −39 |
| 2019 | 239 | 19 | 258 | 313 | −55 |
| 2020 | 297 | 41 | 338 | 405 | −67 |
| 2021 | 506 | 0 | 506 | 331 | +175 |
| 2022 | 573 | 28 | 601 | 828 | −227 |
| 2023 | 628 | 0 | 628 | 716 | −88 |
| 2024 | 946 | 41 | 987 | 708 | +279 |
| 2025 | 594 | 0 | 594 | 492 | +102 |
| **TOT** | **3973** | **129** | **4102** | **4022** | **+80** |

Cumulative CO now **+80 over city** (was −49 after T1, −956 pre-C2). The over-years (2021/2024) will be
rebalanced by C3 phantom-master (1951 Shattuck −163 in CY2024) and reconciled against C1 relabel + the BP
reporting-year work. The convention-dependent flag means **129 of these units can be subtracted in one
query** if the city's convention excludes live-work/sleeping.

## Verification trace
Snapshot integrity `ok`, size-matched · 5/5 rowcount==1 (committed) · fresh-conn verify: all 5
`net_units==value` AND `convention_dependent=true` flagged · idempotency: re-run changed **0 rows**
(no double-append).

## Reverse (undo)
Cleanest: restore `databases/keep_snapshot_2026-06-28_pre-c2-tranche2.db` over the live DB.
Or per-field:
```sql
UPDATE event_classifications
SET net_units = NULL,
    basis_note = 'New + housing indicator'   -- the pre-write note for all 5
WHERE event_id IN (SELECT event_id FROM events
   WHERE source_record_key IN ('B2015-06007','B2019-02824','B2016-03011','B2018-05067','B2021-04949')
     AND event_type_code='permit_finaled') AND housing_role='new_unit' AND is_master=1;
```

## Cross-reference
- Source recovery + spans: `scratch/2026-06-28/c2_count_recovery.csv`
- Tranche 1 (pure dwelling, 15 permits / 907 units): `docs/audit/2026-06-28_c2_tranche1_write.md`
- Still queued: #3 building-identity (B2020-03895) · role-review (B2025-03934) · Accela (B2018-03160).

*Not committed to git. v4 mutation only; this record is the audit trail.*
