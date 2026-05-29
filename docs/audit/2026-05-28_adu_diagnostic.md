# ADU / REV Summation Diagnostic — 2026-05-28

## Headline

D5's CY 2024 ADU stage was producing a net co_units of −84, an
obvious arithmetic error since ADU permits are net-additive. Phase A
investigation surfaced three causally connected issues plus one
adjacent methodology gap. This document captures the diagnosis, the
verification, the fix that landed, and the deferred work.

## The bug (Cause 1 — primary, fixed in this commit's companion)

D5's Cell 14 computed:

```python
co_units = bp_units + rev_finaled["UnitsAdded"].fillna(0).sum() - \
                      rev_finaled["UnitsRemoved"].fillna(0).sum()
```

Berkeley's data convention is to restate the cumulative unit count
on every revision row, not to record marginal deltas. The master
permit row carries (UnitsAdded, UnitsRemoved) representing the
project's net unit change; every finaled REV child carries the
same cumulative values restated. Summing across the master plus k
finaled REVs multiplied the net by (1 + k).

The bug was uniform across all unit types and most visible where
many finaled REVs accumulated on a single master — large multifamily
completions in CY 2024 and CY 2025.

## Phase A verification (read-only)

Across all 56 CY 2024 masters with ≥2 finaled REVs (183 family rows
total):

- 54 / 56 masters: UnitsAdded, UnitsRemoved, NumberUnits all
  identical across every family row including the master
- 2 / 56 masters: UnitsAdded restated identically; only sporadic
  blank NumberUnits varies
- 0 / 56 masters: genuinely marginal (values changing across REVs)

Date-field analysis ruled out "last finaled REV by date" as the
disambiguator: 51 / 56 masters have all finaled REVs sharing one
Finaled Date (Berkeley back-fills REV finaled dates simultaneously).
REV number from PermitNumber would be the only reliable ordering —
but because values are identical across family rows, master-only
aggregation produces the same answer with simpler code.

No 'withdrawn', 'void', 'cancelled', or 'expired' status appears in
finaled-REV rows. No status filter needed.

## Worst-case inflations

| master       | net units | finaled REVs | pre-fix co_units    | post-fix |
|--------------|-----------|--------------|---------------------|----------|
| B2021-00008  | 169       | 17           | 2,873 (~17×)        | 169      |
| B2021-02404  | 113       | ~19          | 2,260 (~20×)        | 113      |
| B2020-01991  | 57        | 7            | 456 (8×)            | 57       |
| B2018-03255  | 63        | 7            | 504 (8×)            | 63       |
| B2021-02225  | 45        | 9            | 450 (10×)           | 45       |
| B2023-02685  | −26       | 3            | −104 (4×)           | −26      |
| B2021-00856  | 1         | 1            | 2                   | 1        |

The 1230 Cedar 2-vs-1 discrepancy (long-flagged as a separate ADU
question) is the same bug.

## Fix applied

`co_units = bp_units` (master-only aggregation). One-line change to
Cell 14. The master row's UnitsAdded − UnitsRemoved is now
authoritative; finaled REV rows are not aggregated. Verified
correct under Berkeley's cumulative-restatement convention (56/56
CY 2024 cases).

## Smoke test (post-fix values)

- 1230 Cedar (B2021-00856): co_units = 1 ✓
- B2023-02685: co_units = −26 ✓
- B2018-03255: co_units = 63 ✓
- B2020-01991: co_units = 57 ✓
- 2650 Telegraph (B2021-02225): co_units = 45 ✓ (CY 2025)
- ADU net co_units CY 2024: −84 → −36

The residual −36 ADU net is expected: Causes 2 and 3 (below) contribute it.

## Cross-year impact

| CY   | net co_units before | after | abs Δ |
|------|---------------------|-------|-------|
| 2018 | 26                  | 26    | 0     |
| 2019 | 234                 | 234   | 0     |
| 2020 | 25                  | 25    | 0     |
| 2021 | 336                 | 334   | 2     |
| 2022 | 345                 | 345   | 0     |
| 2023 | 83                  | 83    | 0     |
| 2024 | 6,498               | 497   | 6,001 |
| 2025 | 5,494               | 261   | 5,233 |

Older cycles essentially unchanged. The impact is concentrated in
CY 2024 and CY 2025, where multi-REV multifamily completions
dominate.

In_both reclassification: 29 CY 2024 rows moved from in_both_unit_
divergent to in_both_clean post-fix; 43 CY 2025 rows similarly.
Membership of d5_only sets unchanged (join-key based, unaffected by
unit values).

## Cause 2 — deferred

Alteration/Demolition masters with cumulative UnitsRemoved.
22 of 58 CY 2024 negative-co rows have rev_sub_count=0 — pure
master-level negatives. When the master is a multi-unit
Alteration/Demolition with UnitsRemoved>0, bp_units = UnitsAdded
− UnitsRemoved goes deeply negative independent of Cause 1.

Fix candidate: Work Type filter excluding non-housing categories.
Scope decision; deferred.

## Cause 3 — deferred

Over-broad ADU classification. `is_adu = (master.ADU == "Yes")`
tags any permit on an ADU-flagged parcel as ADU regardless of Work
Type. Of 811 "ADU" CY 2024 rows:

| Work Type           | rows |
|---------------------|------|
| Alteration          | 453  |
| (blank)             | 171  |
| New                 | 111  |
| Addition/Alteration | 39   |
| Addition            | 21   |
| Sign                | 14   |
| Demolition          | 2    |

Only ~111 "New" rows should plausibly count as new ADU production.
Fix candidate: gate ADU unit count on Work Type="New". Scope
decision; deferred.

## Q5 — ABAG ADU income-tier methodology gap (separate workstream)

HCD has 162 ADU rows for CY 2024 distributing units across
VLI/LI/MOD/Above-MOD tiers via ABAG 30/30/30/10. D5 lumps all units
into BP_ABOVE_MOD_INCOME. Even a Cause-1-corrected D5 will not match
HCD column-by-column without implementing the income-tier split.

Methodology gap distinct from the counting bug. Documented for
future implementation.

## Adjacent finding: parcel-collapse undercounting

Not surfaced by this diagnostic, but identified during the same
session's spot-check work. When a parcel has multiple independent
New-construction permits (separate structures, not REV/DEF children
of one master), D5's one-master-per-parcel grouping keeps only the
highest-units master and demotes siblings, dropping their units.

Quantified blast radius for CY 2024: 28 BP units across 20 HCD rows
(per the bijection ledger's "multi-row same APN" residual). 
Examples: 805 Jones (3 separate 2-unit structures), 2421 Fifth
(3-unit + 1-unit), 1330 / 1340 Haskell (two 1-unit each).

Not fixed by the REV change; structural limit of grouping logic.
Separate fix workstream.
