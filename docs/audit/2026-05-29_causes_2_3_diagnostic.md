# Causes 2 and 3 Diagnostic — 2026-05-29

## Background

Yesterday's REV diagnostic (2026-05-28_adu_diagnostic.md) identified 
three causes of ADU net co_units anomalies in CY 2024. Cause 1 (REV 
cumulative-restatement summation) was fixed yesterday. Causes 2 
and 3 were deferred as separate scope decisions. This document 
captures the Phase A investigation of both across all 8 CY years, 
and the fix landing today.

## Cause 2 — Alteration/Demolition masters with cumulative UnitsRemoved

D5's bp_units computation is UnitsAdded - UnitsRemoved. For a 
multi-unit Alteration or Demolition permit where UnitsRemoved 
exceeds UnitsAdded, bp_units goes negative. These negative values 
get summed into year totals, masking real new units elsewhere.

Phase A characterization across all 8 CY years:

| year | negative_masters | sum_neg_BP | sum_neg_CO |
|------|------------------|------------|------------|
| 2018 | 5                | -32        | -26        |
| 2019 | 3                | -3         | -1         |
| 2020 | 3                | -2         | -3         |
| 2021 | 16               | -15        | -6         |
| 2022 | 102              | -276       | -75        |
| 2023 | 123              | -222       | -269       |
| 2024 | 162              | -338       | -146       |
| 2025 | 198              | -390       | -263       |
| TOTAL| 502              | -1,278     | -789       |

The population is concentrated in CY 2022-2025, growing year over 
year. CY 2025 alone has 198 such masters contributing -390 BP 
units — enough to push the year's total negative.

## Cause 3 — Over-broad ADU classification

D5's is_adu rule tags any permit on an ADU-flagged parcel:

```python
is_adu = (master.ADU == "Yes")
```

This classifies non-housing work on ADU-flagged parcels as ADU 
production. Phase A across all 8 years:

| year | adu_flagged | adu_New | adu_New_with_units | adu_other_types |
|------|-------------|---------|--------------------|-----------------|
| 2018 | 48          | 22      | 15                 | 26              |
| 2019 | 94          | 48      | 32                 | 46              |
| 2020 | 124         | 63      | 49                 | 61              |
| 2021 | 136         | 70      | 59                 | 66              |
| 2022 | 298         | 58      | 49                 | 240             |
| 2023 | 587         | 74      | 56                 | 513             |
| 2024 | 812         | 112     | 62                 | 700             |
| 2025 | 843         | 115     | 72                 | 728             |

The "adu_other_types" column — alterations, signs, demolitions, 
additions on ADU-flagged parcels — grew from 54% of the adu_flagged 
population in CY 2018 to 86% in CY 2025. The actual New-with-units 
ADU production is 62 / 72 for CY 2024-25, in line with HCD's 
reported 102 ADUs (which includes Berkeley's deed-restriction 
breakdown that D5 doesn't reproduce).

## The fix

Both fixes land in the same commit on Cell 14 of D5.

**Cause 3 fix:** tighten is_adu to require Work Type = "New":

```python
is_adu = (master["ADU"] == "Yes") and (master["Work Type"] == "New")
```

**Cause 2 fix:** floor bp_units at 0 for Alteration/Demolition/
Addition-Alteration masters where UnitsRemoved > UnitsAdded:

```python
if master["Work Type"] in ("Alteration", "Demolition", "Addition/Alteration"):
    if (master.get("UnitsRemoved", 0) or 0) > (master.get("UnitsAdded", 0) or 0):
        bp_units = 0
        co_units = 0
```

[The exact code structure depends on D5's current Cell 14 — see 
the fix commit for the canonical implementation.]

## Predicted impact

Combining both fixes (Cause 2 dominates totals, Cause 3 is 
relabeling):

| year | current BP | predicted BP | ΔBP   | current CO | predicted CO | ΔCO   |
|------|------------|--------------|-------|------------|--------------|-------|
| 2018 | 202        | 234          | +32   | 26         | 52           | +26   |
| 2019 | 219        | 222          | +3    | 237        | 238          | +1    |
| 2020 | 528        | 530          | +2    | 28         | 31           | +3    |
| 2021 | 397        | 412          | +15   | 336        | 342          | +6    |
| 2022 | 208        | 484          | +276  | 345        | 420          | +75   |
| 2023 | 287        | 509          | +222  | 84         | 353          | +269  |
| 2024 | 238        | 576          | +338  | 497        | 643          | +146  |
| 2025 | -61        | 329          | +390  | 262        | 525          | +263  |
| total| 2,018      | 3,296        | +1,278| 1,815      | 2,604        | +789  |

These predictions are the Phase B verification target. Per today's 
prediction-table lessons, predictions must be derived from actual 
pipeline state; CHECK 4 confirmed these against current D5 output.

## Methodological notes

**Demolitions are not netted; they are accounted separately.** 
Berkeley's HCD Table A2 has a dedicated "Number of Demolished/
Destroyed Units" column (80 for CY 2024). D5 does not currently 
produce this aggregate as a separate output. The Cause 2 fix 
aligns D5 with HCD's framework by no longer netting demolitions 
against new units; a future workstream should add demolitions as 
a separate D5 output column for completeness.

**The Durant pattern remains a documented data-quality artifact.** 
Phase A CHECK 3 confirmed the Cause 2/3 fix is not at risk from 
the inherited-UnitsAdded pattern. All 33 promoted siblings from 
the parcel-collapse fix are habitable dwellings (verified by 
WorkDescription analysis). The Durant pattern matters for future 
fixes that would trust Work Type = "New" without parcel context.

## Bijection impact

The fix changes unit values but not row membership. Bijection 
join-key-based counts (matched, multi_row_same_apn, c_unmatched) 
are unaffected. Within in_both:
- Many rows will move from unit_divergent to clean as D5's 
  unit values now match HCD's
- Expect substantial in_both_clean increase in CY 2022-2025

## Companion artifacts

- D5 Cell 14 source change: fix(d5) commit
- 8-year ledger regeneration: feat(d7) commit
- Cell 12 regression test baseline updated
